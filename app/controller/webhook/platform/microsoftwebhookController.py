"""
Microsoft Graph Calendar Webhook Handler
"""

import logging
import os
import requests
from typing import Optional

from app.models.webhookModel import WebhookModel
from app.utils.timezoneConverter import TimezoneConverter
from app.controller.webhook.base.basewebhookController import BaseWebhookHandler, HandlerResult

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class MicrosoftWebhookHandler(BaseWebhookHandler):
    platform = "microsoft"

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify(self, request) -> bool:
        """Verify Microsoft webhook via clientState on each notification."""
        try:
            webhook_data = request.get_json(silent=True)
            if not webhook_data:
                # Validation challenge has no body — already handled upstream
                return True

            expected = os.getenv("MICROSOFT_CLIENT_STATE", "meetingbot-secret")
            for notification in webhook_data.get("value", []):
                if notification.get("clientState") != expected:
                    logger.error(f"[Microsoft] Invalid clientState: {notification.get('clientState')}")
                    return False

            return True

        except Exception as e:
            logger.error(f"[Microsoft] Verification error: {e}")
            return False

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def handle(self, request) -> HandlerResult:
        """Process all notifications in the Microsoft webhook payload."""
        try:
            webhook_data = request.get_json(silent=True) or {}
            notifications = webhook_data.get("value", [])

            processed = 0
            for notification in notifications:
                try:
                    if self._process_notification(notification):
                        processed += 1
                except Exception as e:
                    logger.error(f"[Microsoft] Notification processing error: {e}")
                    continue

            return {"status": "processed", "meetings_processed": processed}, 200

        except Exception as e:
            logger.error(f"[Microsoft] Handle error: {e}")
            return {"error": "Failed to handle event"}, 500

    # ------------------------------------------------------------------
    # Per-notification logic
    # ------------------------------------------------------------------

    def _process_notification(self, notification: dict) -> bool:
        subscription_id = notification.get("subscriptionId")
        resource = notification.get("resource")  # e.g. "Users/abc/Events/xyz"

        if not resource:
            logger.warning("[Microsoft] Notification missing 'resource' field")
            return False

        webhook = WebhookModel.query.filter_by(
            platform="microsoft", channel_id=subscription_id, is_active=True
        ).first()
        if not webhook:
            logger.error(f"[Microsoft] No active webhook for subscription: {subscription_id}")
            return False

        access_token = self.get_valid_token(webhook)
        if not access_token:
            return False

        # Fetch full event from Graph API
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{GRAPH_BASE}/{resource}", headers=headers)

        if response.status_code == 401:
            logger.warning("[Microsoft] 401 — forcing token refresh")
            from app.services.tokenService import TokenService
            access_token = TokenService.refresh_access_token_if_needed(webhook)
            if not access_token:
                return False
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(f"{GRAPH_BASE}/{resource}", headers=headers)

        response.raise_for_status()
        event_data = response.json()

        meeting_link = self._extract_meeting_link(event_data)
        if not meeting_link:
            logger.info(f"[Microsoft] No meeting link for: {event_data.get('subject')}")
            return False

        start_raw = event_data.get("start", {}).get("dateTime", "")
        end_raw = event_data.get("end", {}).get("dateTime", "")

        meeting = {
            "id": event_data.get("id"),
            "title": event_data.get("subject", "No Title"),
            "start_time": TimezoneConverter.convert_to_ist_or_keep(start_raw) if start_raw else "",
            "end_time": TimezoneConverter.convert_to_ist_or_keep(end_raw) if end_raw else "",
            "meeting_link": meeting_link,
            "platform": "microsoft",
        }

        self.store_and_schedule(meeting, webhook.user_id)
        logger.info(f"[Microsoft] Processed meeting: {meeting['title']}")
        return True

    # ------------------------------------------------------------------
    # Meeting link extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_meeting_link(event: dict) -> Optional[str]:
        """Try all known locations for a Teams / meeting link."""
        # Online meeting URL field
        if event.get("onlineMeetingUrl"):
            return event["onlineMeetingUrl"]

        # onlineMeeting object
        online = event.get("onlineMeeting") or {}
        if online.get("joinUrl"):
            return online["joinUrl"]

        # Body HTML fallback
        body = event.get("body", {}).get("content", "")
        for keyword in ["teams.microsoft.com", "zoom.us/j", "meet.google.com"]:
            if keyword in body:
                for token in body.split():
                    if keyword in token:
                        # Strip HTML attributes that may be attached
                        url = token.strip('href="').rstrip('">')
                        if url.startswith("http"):
                            return url

        return None