"""
Google Calendar Webhook Handler
"""

import logging
import requests
from typing import Dict, Any

from app.models.webhookModel import WebhookModel
from app.services.CalendarServiceFactory import CalendarServiceFactory
from app.utils.timezoneConverter import TimezoneConverter
from app.controller.webhook.base.basewebhookController import (
    BaseWebhookHandler,
    HandlerResult,
)

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


class GoogleWebhookHandler(BaseWebhookHandler):
    platform = "google"

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify(self, request) -> bool:
        """Verify Google webhook via channel_id / resource_id headers."""
        try:
            channel_id = request.headers.get("X-Goog-Channel-ID")
            resource_id = request.headers.get("X-Goog-Resource-ID")

            if not channel_id or not resource_id:
                logger.error(
                    "[Google] Missing X-Goog-Channel-ID or X-Goog-Resource-ID headers"
                )
                return False

            webhook = WebhookModel.query.filter_by(channel_id=channel_id).first()
            if not webhook:
                logger.error(f"[Google] No webhook for channel_id: {channel_id}")
                return False

            if not webhook.is_active:
                logger.info(f"[Google] Webhook {channel_id} is inactive")
                return False

            logger.info(
                f"[Google] Webhook validation successful for channel: {channel_id}"
            )
            return True

        except Exception as e:
            logger.error(f"[Google] Verification error: {e}")
            return False

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def handle(self, request) -> HandlerResult:
        """Route Google webhook to sync or event-change handler."""
        channel_id = request.headers.get("X-Goog-Channel-ID")
        resource_id = request.headers.get("X-Goog-Resource-ID")
        resource_state = request.headers.get("X-Goog-Resource-State")
        resource_uri = request.headers.get("X-Goog-Resource-URI")

        if resource_state == "sync":
            return self._handle_initial_sync(channel_id)

        return self._handle_event_change(channel_id, resource_id, resource_uri)

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------

    def _handle_initial_sync(self, channel_id: str) -> HandlerResult:
        """Fetch and store all upcoming meetings when channel first activates."""
        webhook = self.get_webhook_by_channel(channel_id)
        if not webhook:
            return {"error": "Webhook not found"}, 404

        access_token = self.get_valid_token(webhook)
        if not access_token:
            return {"error": "Token refresh failed"}, 500

        try:
            calendar_service = CalendarServiceFactory.create_service("google")
            events = calendar_service.get_upcoming_meetings(
                access_token=access_token,
                refresh_token=webhook.refresh_token,
            )

            count = 0
            for event in events:
                if event.get("meeting_link"):
                    self.store_and_schedule(event, webhook.user_id)
                    count += 1

            logger.info(
                f"[Google] Initial sync: {count} meetings for channel {channel_id}"
            )
            return {"status": "sync_completed", "events_processed": count}, 200

        except Exception as e:
            logger.error(f"[Google] Initial sync error: {e}")
            return {"error": "Failed to handle initial sync"}, 500

    # ------------------------------------------------------------------
    # Event change
    # ------------------------------------------------------------------

    def _handle_event_change(self, channel_id: str, resource_id: str, resource_uri: str) -> HandlerResult:
        """Fetch changed events from Google and store/schedule them."""
        webhook = self.get_webhook_by_channel(channel_id)
        if not webhook:
            return {"error": "Webhook not found"}, 404

        access_token = self.get_valid_token(webhook)
        if not access_token:
            return {"error": "Token refresh failed"}, 500

        try:
            # Prefer the resource_uri from the header; fall back to primary calendar events
            url = resource_uri or f"{GOOGLE_CALENDAR_API}/calendars/primary/events"
            headers = {"Authorization": f"Bearer {access_token}"}

            response = requests.get(url, headers=headers)

            # --- Retry once on 401 with a forced token refresh ---
            if response.status_code == 401:
                logger.warning("[Google] 401 on event fetch — forcing token refresh")
                from app.services.tokenService import TokenService

                access_token = TokenService.refresh_access_token_if_needed(webhook)
                if not access_token:
                    return {"error": "Token refresh failed after 401"}, 500
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(url, headers=headers)

            response.raise_for_status()
            event_data = response.json()

            # Calendar feed returns 'items'; a single event does not
            if "items" in event_data:
                return self._process_event_list(event_data["items"], webhook)

            return self._process_single_event(event_data, webhook)

        except Exception as e:
            logger.error(f"[Google] Event change error: {e}")
            return {"error": "Failed to handle event change"}, 500

    def _process_event_list(self, events: list, webhook: WebhookModel) -> HandlerResult:
        count = 0
        for raw_event in events:
            if self._is_meeting(raw_event):
                meeting = self._parse_event(raw_event)
                self.store_and_schedule(meeting, webhook.user_id)
                count += 1
        logger.info(f"[Google] Processed {count} meetings from calendar feed")
        return {"status": "processed_calendar_feed", "meetings_found": count}, 200

    def _process_single_event(self, raw_event: dict, webhook: WebhookModel) -> HandlerResult:
        if self._is_meeting(raw_event):
            meeting = self._parse_event(raw_event)
            self.store_and_schedule(meeting, webhook.user_id)
            logger.info(
                f"[Google] Stored meeting: {meeting['title']} at {meeting['start_time']}"
            )
            return {"status": "meeting_stored"}, 200

        logger.info(f"[Google] Event is not a meeting: {raw_event.get('summary')}")
        return {"status": "not_meeting"}, 200

    # ------------------------------------------------------------------
    # Event parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_meeting(event: dict) -> bool:
        return bool(
            event.get("hangoutLink")
            or event.get("conferenceData")
            or (
                event.get("description")
                and any(
                    kw in event["description"].lower()
                    for kw in ["meet.google.com", "hangouts.google.com", "zoom.us"]
                )
            )
        )

    @staticmethod
    def _parse_event(event: dict) -> dict:
        """Convert a raw Google Calendar event into the standard meeting dict."""
        # Resolve meeting link
        meeting_link = event.get("hangoutLink")
        if not meeting_link:
            for ep in event.get("conferenceData", {}).get("entryPoints", []):
                if ep.get("entryPointType") == "video":
                    meeting_link = ep.get("uri")
                    break
        if not meeting_link and event.get("description"):
            for line in event["description"].split("\n"):
                if "meet.google.com" in line or "hangouts.google.com" in line:
                    meeting_link = line.strip()
                    break

        start_data = event.get("start", {})
        end_data = event.get("end", {})
        tz = start_data.get("timeZone") or end_data.get("timeZone")
        start_raw = start_data.get("dateTime", start_data.get("date", ""))
        end_raw = end_data.get("dateTime", end_data.get("date", ""))

        return {
            "id": event["id"],
            "title": event.get("summary", "No Title"),
            "start_time": (
                TimezoneConverter.convert_to_ist_or_keep(start_raw, tz)
                if start_raw
                else start_raw
            ),
            "end_time": (
                TimezoneConverter.convert_to_ist_or_keep(end_raw, tz)
                if end_raw
                else end_raw
            ),
            "meeting_link": meeting_link,
            "platform": "google",
            "timezone": tz,
        }
