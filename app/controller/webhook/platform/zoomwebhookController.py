"""
Zoom Webhook Handler
Handles: meeting.created, meeting.updated, meeting.started, meeting.ended, meeting.deleted
"""

import hashlib
import hmac
import logging
import os
from typing import Optional

from app.models.webhookModel import WebhookModel
from app.models.jobModel import JobModel
from app.extension import db
from app.utils.timezoneConverter import TimezoneConverter
from app.controller.webhook.base.basewebhookController import BaseWebhookHandler, HandlerResult

logger = logging.getLogger(__name__)


class ZoomWebhookHandler(BaseWebhookHandler):
    platform = "zoom"

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify(self, request) -> bool:
        """Verify Zoom webhook via HMAC-SHA256 signature."""
        try:
            zoom_secret = os.getenv("ZOOM_SECRET_KEY")
            if not zoom_secret:
                logger.error("[Zoom] ZOOM_SECRET_KEY not set")
                return False

            # URL validation challenge has no signature — allow it through
            # it gets handled in handle() before any auth matters
            body = request.get_data(as_text=True)
            if '"endpoint.url_validation"' in body:
                return True

            signature = request.headers.get("x-zm-signature", "")
            if not signature.startswith("v0="):
                logger.error(f"[Zoom] Invalid signature format: {signature}")
                return False

            received_hash = signature[3:]
            message = f"v0:{body}"
            expected_hash = hmac.new(
                zoom_secret.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()

            valid = hmac.compare_digest(expected_hash, received_hash)
            if not valid:
                logger.error("[Zoom] Signature mismatch")
            return valid

        except Exception as e:
            logger.error(f"[Zoom] Verification error: {e}")
            return False

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def handle(self, request) -> HandlerResult:
        """Route Zoom webhook to the appropriate handler by event type."""
        try:
            webhook_data = request.get_json(silent=True) or {}
            event_type = webhook_data.get("event", "")

            logger.info(f"[Zoom] Received event: {event_type}")

            # URL validation challenge — must respond immediately
            if event_type == "endpoint.url_validation":
                return self._handle_url_validation(webhook_data)

            # Route by event type
            handlers = {
                "meeting.created": self._handle_meeting_created,
                "meeting.updated": self._handle_meeting_updated,
                "meeting.started": self._handle_meeting_started,
                "meeting.ended":   self._handle_meeting_ended,
                "meeting.deleted": self._handle_meeting_deleted,
            }

            handler = handlers.get(event_type)
            if not handler:
                logger.info(f"[Zoom] Ignoring unhandled event: {event_type}")
                return {"status": "ignored", "event": event_type}, 200

            return handler(webhook_data)

        except Exception as e:
            logger.error(f"[Zoom] Handle error: {e}")
            return {"error": "Failed to handle event"}, 500

    # ------------------------------------------------------------------
    # URL validation
    # ------------------------------------------------------------------

    def _handle_url_validation(self, data: dict) -> HandlerResult:
        """Respond to Zoom's endpoint validation challenge."""
        token = data.get("payload", {}).get("plainToken", "")
        secret = os.getenv("ZOOM_SECRET_KEY", "")
        hashed = hmac.new(
            secret.encode(), token.encode(), hashlib.sha256
        ).hexdigest()
        logger.info("[Zoom] Responded to URL validation challenge")
        return {"plainToken": token, "encryptedToken": hashed}, 200

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _handle_meeting_created(self, webhook_data: dict) -> HandlerResult:
        """
        Store meeting and schedule bot to join buffer_minutes before start.
        Default buffer is 10 minutes — bot joins early so it's ready when
        the host starts.
        """
        meeting, webhook = self._extract_meeting_and_webhook(webhook_data)
        if not meeting or not webhook:
            return {"error": "Could not resolve meeting or webhook"}, 404

        if not meeting.get("meeting_link"):
            logger.info(f"[Zoom] No join URL for created meeting: {meeting.get('title')} — skipping")
            return {"status": "no_join_url"}, 200

        # store_and_schedule uses buffer_minutes=10 by default for non-microsoft platforms
        self.store_and_schedule(meeting, webhook.user_id)
        logger.info(f"[Zoom] Stored and scheduled: {meeting['title']} at {meeting['start_time']}")
        return {"status": "meeting_stored"}, 200

    def _handle_meeting_updated(self, webhook_data: dict) -> HandlerResult:
        """
        Update existing job with new meeting details.
        Also reschedules the bot if the start time changed.
        """
        meeting, webhook = self._extract_meeting_and_webhook(webhook_data)
        if not meeting or not webhook:
            return {"error": "Could not resolve meeting or webhook"}, 404

        if not meeting.get("meeting_link"):
            logger.info(f"[Zoom] No join URL for updated meeting: {meeting.get('title')} — skipping")
            return {"status": "no_join_url"}, 200

        # Remove existing APScheduler job so it gets rescheduled with new time
        from app.services.schedulerService import scheduler_service
        job_id = f"bot_{meeting['id']}_{webhook.user_id}"
        scheduler_service.remove_job(job_id)

        # store_and_schedule will update the DB row and reschedule
        self.store_and_schedule(meeting, webhook.user_id)
        logger.info(f"[Zoom] Updated and rescheduled: {meeting['title']} at {meeting['start_time']}")
        return {"status": "meeting_updated"}, 200

    def _handle_meeting_started(self, webhook_data: dict) -> HandlerResult:
        """
        Host just started the meeting — trigger bot immediately.
        This is a safety net: if the bot wasn't already joining
        (e.g. meeting started earlier than scheduled), join right now.
        """
        meeting, webhook = self._extract_meeting_and_webhook(webhook_data)
        if not meeting or not webhook:
            return {"error": "Could not resolve meeting or webhook"}, 404

        if not meeting.get("meeting_link"):
            logger.info(f"[Zoom] No join URL for started meeting: {meeting.get('title')}")
            return {"status": "no_join_url"}, 200

        # Check if a job exists and isn't already running
        job = JobModel.query.filter_by(
            meeting_id=meeting["id"], user_id=webhook.user_id
        ).first()

        if job and job.status in ("running", "In Progress", "Completed"):
            logger.info(f"[Zoom] Bot already {job.status} for: {meeting['title']} — skipping")
            return {"status": "already_running"}, 200

        # Trigger bot immediately — meeting is live now
        from app.services.schedulerService import scheduler_service
        logger.info(f"[Zoom] Meeting started — triggering bot immediately: {meeting['title']}")
        scheduler_service._trigger_bot(meeting, webhook.user_id)
        return {"status": "bot_triggered"}, 200

    def _handle_meeting_ended(self, webhook_data: dict) -> HandlerResult:
        """
        Meeting ended — mark the job as completed if it's still running.
        The bot's own detect_end() will also catch this, but this is a
        server-side safety net.
        """
        payload = webhook_data.get("payload", {})
        meeting_obj = payload.get("object", {})
        meeting_id = str(meeting_obj.get("uuid") or meeting_obj.get("id", ""))
        account_id = payload.get("account_id") or meeting_obj.get("host_id")

        webhook = self._get_webhook_by_account(account_id)
        if not webhook:
            return {"error": "Webhook not found"}, 404

        job = JobModel.query.filter_by(
            meeting_id=meeting_id, user_id=webhook.user_id
        ).first()

        if job and job.status == "running":
            job.status = "Completed"
            db.session.commit()
            logger.info(f"[Zoom] Marked job as Completed for ended meeting: {meeting_obj.get('topic')}")

        return {"status": "meeting_ended"}, 200

    def _handle_meeting_deleted(self, webhook_data: dict) -> HandlerResult:
        """
        Meeting was deleted — cancel the scheduled bot job and mark as cancelled.
        """
        payload = webhook_data.get("payload", {})
        meeting_obj = payload.get("object", {})
        meeting_id = str(meeting_obj.get("uuid") or meeting_obj.get("id", ""))
        account_id = payload.get("account_id") or meeting_obj.get("host_id")

        webhook = self._get_webhook_by_account(account_id)
        if not webhook:
            return {"error": "Webhook not found"}, 404

        job = JobModel.query.filter_by(
            meeting_id=meeting_id, user_id=webhook.user_id
        ).first()

        if job:
            # Remove from APScheduler
            from app.services.schedulerService import scheduler_service
            job_id = f"bot_{meeting_id}_{webhook.user_id}"
            scheduler_service.remove_job(job_id)

            # Mark as cancelled
            job.status = "cancelled"
            db.session.commit()
            logger.info(f"[Zoom] Cancelled job for deleted meeting: {meeting_obj.get('topic')}")
        else:
            logger.info(f"[Zoom] No job found for deleted meeting: {meeting_obj.get('topic')} — nothing to cancel")

        return {"status": "meeting_cancelled"}, 200

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _extract_meeting_and_webhook(self, webhook_data: dict):
        """
        Extract standardized meeting dict and matching WebhookModel from payload.
        Returns (meeting, webhook) or (None, None) on failure.
        """
        payload = webhook_data.get("payload", {})
        meeting_obj = payload.get("object", {})
        account_id = payload.get("account_id") or meeting_obj.get("host_id")

        if not account_id:
            logger.error("[Zoom] Missing account_id / host_id in payload")
            return None, None

        webhook = self._get_webhook_by_account(account_id)
        if not webhook:
            logger.error(f"[Zoom] No active webhook for account: {account_id}")
            return None, None

        start_raw = meeting_obj.get("start_time", "")
        meeting = {
            "id": str(meeting_obj.get("uuid") or meeting_obj.get("id", "")),
            "title": meeting_obj.get("topic", "No Title"),
            "start_time": TimezoneConverter.convert_to_ist_or_keep(start_raw) if start_raw else "",
            "end_time": "",   # Zoom rarely provides end time in webhook payload
            "meeting_link": meeting_obj.get("join_url", ""),
            "platform": "zoom",
        }

        if not meeting["id"]:
            logger.error("[Zoom] No meeting ID in payload")
            return None, None

        return meeting, webhook

    def _get_webhook_by_account(self, account_id: str) -> Optional[WebhookModel]:
        """Look up webhook by Zoom account_id stored in calendar_email."""
        if not account_id:
            return None
        return WebhookModel.query.filter_by(
            platform="zoom", is_active=True, calendar_email=account_id
        ).first()