"""
Zoom Webhook Handler
"""

import hashlib
import hmac
import logging
import os

from app.models.webhookModel import WebhookModel
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

            signature = request.headers.get("x-zm-signature", "")
            if not signature.startswith("v0="):
                logger.error(f"[Zoom] Invalid signature format: {signature}")
                return False

            received_hash = signature[3:]
            body = request.get_data(as_text=True)
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
        """Handle Zoom meeting event."""
        try:
            webhook_data = request.get_json(silent=True) or {}

            # Zoom URL validation challenge
            if webhook_data.get("event") == "endpoint.url_validation":
                return self._handle_url_validation(webhook_data)

            return self._handle_meeting_event(webhook_data)

        except Exception as e:
            logger.error(f"[Zoom] Handle error: {e}")
            return {"error": "Failed to handle event"}, 500

    # ------------------------------------------------------------------
    # URL validation (Zoom requires this on webhook setup)
    # ------------------------------------------------------------------

    def _handle_url_validation(self, data: dict) -> HandlerResult:
        import hashlib, hmac, os
        token = data.get("payload", {}).get("plainToken", "")
        secret = os.getenv("ZOOM_SECRET_KEY", "")
        hashed = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        return {"plainToken": token, "encryptedToken": hashed}, 200

    # ------------------------------------------------------------------
    # Meeting event
    # ------------------------------------------------------------------

    def _handle_meeting_event(self, webhook_data: dict) -> HandlerResult:
        payload = webhook_data.get("payload", {})
        meeting = payload.get("object", {})
        account_id = payload.get("account_id") or meeting.get("host_id")

        if not account_id:
            logger.error("[Zoom] Missing account_id / host_id in payload")
            return {"error": "Missing user identifier"}, 400

        # account_id is stored in calendar_email for Zoom
        webhook = WebhookModel.query.filter_by(
            platform="zoom", is_active=True, calendar_email=account_id
        ).first()
        if not webhook:
            logger.error(f"[Zoom] No active webhook for account: {account_id}")
            return {"error": "Webhook not found"}, 404

        zoom_meeting = {
            "id": meeting.get("uuid"),
            "title": meeting.get("topic", "No Title"),
            "start_time": meeting.get("start_time", ""),
            "end_time": meeting.get("start_time", ""),  # Zoom rarely provides end time
            "meeting_link": meeting.get("join_url", ""),
            "platform": "zoom",
        }

        if not zoom_meeting["id"] or not zoom_meeting["meeting_link"]:
            logger.warning(f"[Zoom] Incomplete meeting data: {zoom_meeting}")
            return {"error": "Incomplete meeting data"}, 400

        self.store_and_schedule(zoom_meeting, webhook.user_id)
        logger.info(f"[Zoom] Stored meeting: {zoom_meeting['title']} at {zoom_meeting['start_time']}")
        return {"status": "meeting_stored"}, 200