"""
Base Webhook Handler
All platform-specific handlers inherit from this.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

from app.models.webhookModel import WebhookModel
from app.models.jobModel import JobModel
from app.services.tokenService import TokenService
from app.utils.timezoneConverter import TimezoneConverter
from app.extension import db
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Standard meeting dict shape used across all platforms:
# {
#   'id': str,
#   'title': str,
#   'start_time': str (IST iso),
#   'end_time': str (IST iso),
#   'meeting_link': str,
#   'platform': str,
# }

MeetingDict = Dict[str, Any]
HandlerResult = Tuple[Dict[str, Any], int]


class BaseWebhookHandler(ABC):
    """Abstract base for platform webhook handlers"""

    platform: str = ""  # subclasses must set this

    # ------------------------------------------------------------------
    # Abstract interface — each platform implements these
    # ------------------------------------------------------------------

    @abstractmethod
    def verify(self, request) -> bool:
        """Verify the incoming request is authentic. Return True/False."""
        ...

    @abstractmethod
    def handle(self, request) -> HandlerResult:
        """Entry point called by the route. Returns (response_dict, status_code)."""
        ...

    # ------------------------------------------------------------------
    # Shared helpers available to all subclasses
    # ------------------------------------------------------------------

    def get_webhook_by_channel(self, channel_id: str) -> Optional[WebhookModel]:
        return WebhookModel.query.filter_by(
            platform=self.platform, channel_id=channel_id, is_active=True
        ).first()

    def get_valid_token(self, webhook: WebhookModel) -> Optional[str]:
        """Get a valid (possibly refreshed) access token."""
        token = TokenService.get_valid_access_token(webhook)
        if not token:
            logger.error(
                f"[{self.platform}] Could not obtain valid access token "
                f"for webhook {webhook.webhook_id}"
            )
        return token

    def store_and_schedule(self, meeting: MeetingDict, user_id: int) -> bool:
        """
        Persist meeting info and schedule a bot job.
        Returns True on success.
        """
        try:
            existing = JobModel.query.filter_by(
                meeting_id=meeting["id"], user_id=user_id
            ).first()

            scheduled_datetime = self._parse_ist_datetime(meeting.get("start_time", ""))

            if existing:
                existing.meeting_title = meeting["title"]
                existing.meeting_link = meeting["meeting_link"]
                existing.job_url = meeting["meeting_link"]
                existing.scheduled_time = scheduled_datetime
                existing.status = "scheduled"
                logger.info(f"[{self.platform}] Updated meeting: {meeting['title']}")
            else:
                job = JobModel(
                    user_id=user_id,
                    job_url=meeting["meeting_link"],
                    meeting_id=meeting["id"],
                    meeting_title=meeting["title"],
                    meeting_link=meeting["meeting_link"],
                    platform=meeting["platform"],
                    scheduled_time=scheduled_datetime,
                    status="pending",
                )
                db.session.add(job)
                logger.info(f"[{self.platform}] Stored new meeting: {meeting['title']}")

            db.session.commit()

            # Schedule bot
            try:
                from app.services.schedulerService import scheduler_service
                scheduler_service.schedule_bot_job(meeting, user_id)
            except Exception as e:
                logger.error(f"[{self.platform}] Scheduler error for '{meeting['title']}': {e}")
                # Don't fail storage if scheduling fails

            return True

        except Exception as e:
            logger.error(f"[{self.platform}] store_and_schedule error: {e}")
            db.session.rollback()
            return False

    # ------------------------------------------------------------------
    # Private utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_ist_datetime(ist_str: str) -> Optional[datetime]:
        if not ist_str:
            return None
        try:
            return datetime.fromisoformat(ist_str)
        except ValueError:
            return None