import logging
import pytz
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from app.models.jobModel import JobModel
from app.models.userIntegrationModel import UserIntegration
from app.extension import db
from app.utils.timezoneConverter import TimezoneConverter

logger = logging.getLogger(__name__)


class SchedulerService:

    def __init__(self):
        self.scheduler: Optional[BackgroundScheduler] = None
        self.app = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self):

        self.app = current_app._get_current_object()
        self.scheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            executors={"default": ThreadPoolExecutor(20)},
            timezone="UTC",
        )
        logger.info("SchedulerService initialized")

    def start(self):
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
            self.schedule_all_pending_jobs()
            self.schedule_fallback_polling()
            self.schedule_microsoft_subscription_renewal()

    def stop(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    # ------------------------------------------------------------------
    # Core: store + schedule (single owner of this logic)
    # ------------------------------------------------------------------

    def store_and_schedule(self, meeting: Dict[str, Any], user_id: int) -> bool:
        """
        Persist meeting to JobModel and schedule a bot job.
        Idempotent — updates if a job for meeting_id + user_id already exists.
        Returns True on success.
        """
        try:
            scheduled_datetime = self._parse_ist_datetime(meeting.get("start_time", ""))

            existing = JobModel.query.filter_by(
                meeting_id=meeting["id"], user_id=user_id
            ).first()

            if existing:
                existing.meeting_title = meeting["title"]
                existing.meeting_link = meeting["meeting_link"]
                existing.job_url = meeting["meeting_link"]
                existing.scheduled_time = scheduled_datetime
                existing.status = "scheduled"
                logger.info(f"[Scheduler] Updated meeting: {meeting['title']}")
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
                logger.info(f"[Scheduler] Stored new meeting: {meeting['title']}")

            db.session.commit()
            self.schedule_bot_job(meeting, user_id)
            return True

        except Exception as e:
            logger.error(f"[Scheduler] store_and_schedule error: {e}")
            db.session.rollback()
            return False

    # ------------------------------------------------------------------
    # Bot scheduling
    # ------------------------------------------------------------------

    def schedule_bot_job(
        self, event: Dict[str, Any], user_id: int, buffer_minutes: int = 2
    ) -> bool:
        """Schedule the bot to join a meeting. For Microsoft, joins exactly on time."""
        try:
            start_time_str = event.get("start_time")
            if not start_time_str:
                logger.error(f"[Scheduler] No start_time in event: {event}")
                return False

            start_utc = self._convert_ist_to_utc(start_time_str)
            if not start_utc:
                return False

            platform = event.get("platform", "").lower()
            run_at = (
                start_utc
                if platform == "microsoft"
                else start_utc - timedelta(minutes=buffer_minutes)
            )

            now = datetime.now(timezone.utc)
            if run_at <= now:
                # Meeting already started — join immediately if not ended
                if start_utc + timedelta(hours=2) > now:
                    logger.info(
                        f"[Scheduler] Meeting in progress, triggering immediately: {event.get('title')}"
                    )
                    self._trigger_bot(event, user_id)
                    return True
                else:
                    logger.info(
                        f"[Scheduler] Meeting likely ended: {event.get('title')}"
                    )
                    return False

            job_id = f"bot_{event.get('id')}_{user_id}"
            if self.scheduler and self.scheduler.get_job(job_id):
                logger.info(f"[Scheduler] Job already scheduled: {job_id}")
                return False

            join_desc = (
                "at start"
                if platform == "microsoft"
                else f"{buffer_minutes} mins early"
            )
            self.scheduler.add_job(
                func=self._trigger_bot,
                trigger=DateTrigger(run_date=run_at),
                id=job_id,
                args=[event, user_id],
                name=f"Bot: {event.get('title', 'Unknown')} ({join_desc})",
            )
            logger.info(f"[Scheduler] Scheduled {job_id} at {run_at} ({join_desc})")
            return True

        except Exception as e:
            logger.error(f"[Scheduler] schedule_bot_job error: {e}")
            return False

    def _trigger_bot(self, event: Dict[str, Any], user_id: int):
        """Called by APScheduler to actually launch the bot."""
        try:

            with self.app.app_context():
                meeting_link = event.get("meeting_link")
                if not meeting_link:
                    logger.error(f"[Scheduler] No meeting link: {event}")
                    return

                job = (
                    JobModel.query.filter_by(
                        meeting_id=event.get("id"), user_id=user_id
                    )
                    .with_for_update()
                    .first()
                )

                if not job:
                    logger.error(
                        f"[Scheduler] No job row for meeting {event.get('id')}, user {user_id}"
                    )
                    return

                if job.status in ("running", "In Progress", "Completed"):
                    logger.info(f"[Scheduler] Job already {job.status}: {job.job_id}")
                    return

                job.status = "running"
                db.session.commit()

                self._create_bot_directly(
                    user_id=user_id,
                    meeting_link=meeting_link,
                    platform=event.get("platform"),
                    meeting_title=event.get("title"),
                    meeting_id=event.get("id"),
                )

        except Exception as e:
            logger.error(
                f"[Scheduler] _trigger_bot error for {event.get('title')}: {e}"
            )
            try:

                with self.app.app_context():
                    job = JobModel.query.filter_by(
                        meeting_id=event.get("id"), user_id=user_id
                    ).first()
                    if job:
                        job.status = "failed"
                        job.error_message = str(e)
                        db.session.commit()
            except Exception:
                pass

    def _create_bot_directly(
        self,
        user_id: int,
        meeting_link: str,
        platform: str,
        meeting_title: str,
        meeting_id: str,
    ):
        """Launch bot task. Reuses existing JobModel row — does NOT create a new one."""
        try:

            from app.models.userModel import userModel
            from app.task.bot_tasks import start_bot

            with self.app.app_context():
                user = userModel.query.filter_by(user_id=user_id).first()
                if not user:
                    logger.error(f"[Scheduler] User not found: {user_id}")
                    return

                # Find the existing job row (created by store_and_schedule)
                job = JobModel.query.filter_by(
                    meeting_id=meeting_id, user_id=user_id
                ).first()
                if not job:
                    logger.error(f"[Scheduler] No job row for meeting {meeting_id}")
                    return

                user.meetings += 1
                job.audio_path = (
                    f"app/recordings/{user.username}_meeting_{user.meetings}_audio.mp3"
                )
                db.session.commit()

                start_bot.delay(job.job_id, job.audio_path, meeting_link)
                logger.info(f"[Scheduler] Bot started for: {meeting_title}")

        except Exception as e:
            logger.error(f"[Scheduler] _create_bot_directly error: {e}")
            raise

    # ------------------------------------------------------------------
    # Recovery and polling
    # ------------------------------------------------------------------

    def schedule_all_pending_jobs(self):
        """On startup, re-schedule any jobs that are still pending in the DB."""
        try:

            with self.app.app_context():
                pending = JobModel.query.filter_by(status="pending").all()
                count = 0
                for job in pending:
                    if job.scheduled_time and job.meeting_id:
                        event = {
                            "id": job.meeting_id,
                            "title": job.meeting_title,
                            "start_time": job.scheduled_time.isoformat(),
                            "meeting_link": job.meeting_link,
                            "platform": job.platform,
                        }
                        if self.schedule_bot_job(event, job.user_id):
                            job.status = "scheduled"
                            count += 1
                db.session.commit()
                logger.info(f"[Scheduler] Recovered {count} pending jobs on startup")
        except Exception as e:
            logger.error(f"[Scheduler] schedule_all_pending_jobs error: {e}")

    def schedule_fallback_polling(self):
        self.scheduler.add_job(
            func=self._fallback_polling,
            trigger=IntervalTrigger(minutes=30),
            id="fallback_polling",
            name="Fallback Calendar Polling",
            replace_existing=True,
        )
        logger.info("[Scheduler] Fallback polling every 30 minutes")

    def _fallback_polling(self):
        """
        Poll calendar APIs for users without active webhooks.

        FIX: Previously, all meetings from all integrations were processed in a
        single flat loop. This caused the first platform encountered (e.g. Google)
        to flood the scheduler with bot jobs, starving all other platforms
        (e.g. Microsoft, Zoom) of scheduling slots.

        The fix collects upcoming meetings from EVERY integration first, then
        interleaves them round-robin by platform before scheduling. This ensures
        each platform gets an equal share of bot slots regardless of meeting count.
        """
        try:

            from app.controller.calendar.calendarController import CalendarController
            from app.services.tokenService import TokenService

            with self.app.app_context():
                integrations = UserIntegration.query.filter_by(is_active=True).all()

                # ── Step 1: Collect meetings grouped by platform ──────────────
                # Key: platform name  →  Value: list of (meeting, user_id) tuples
                meetings_by_platform: Dict[str, list] = {}

                for integration in integrations:
                    try:
                        calendar_controller = CalendarController()
                        service = calendar_controller._get_service(integration.platform)
                        access_token = TokenService.get_valid_access_token(integration)
                        if not access_token:
                            continue

                        meetings = service.get_upcoming_meetings(
                            access_token=access_token,
                            refresh_token=integration.refresh_token,
                        )

                        # Only keep meetings that have a link and are not already
                        # scheduled/running to avoid redundant store_and_schedule calls.

                        already_scheduled_ids = set()

                        for job in JobModel.query.filter(
                            JobModel.user_id == integration.user_id
                        ).all():

                            if job.status in (
                                "scheduled",
                                "running",
                                "In progress",
                                "Bot Created",
                                "Meeting Started",
                                "Recording Started",
                                "Completed",
                            ):
                                already_scheduled_ids.add(job.meeting_id)

                            elif job.status == "Failed":
                                if job.scheduled_time:
                                    scheduled_utc = self._convert_ist_to_utc(
                                        job.scheduled_time.isoformat()
                                    )

                                    if scheduled_utc:
                                        now = datetime.now(timezone.utc)
                                        mins_since_start = (
                                            now - scheduled_utc
                                        ).total_seconds() / 60

                                        if mins_since_start > 30:
                                            already_scheduled_ids.add(job.meeting_id)
                                    else:
                                        already_scheduled_ids.add(job.meeting_id)

                        new_meetings = [
                            m
                            for m in meetings
                            if m.get("meeting_link")
                            and m.get("id") not in already_scheduled_ids
                        ]

                        platform = integration.platform
                        if platform not in meetings_by_platform:
                            meetings_by_platform[platform] = []
                        meetings_by_platform[platform].extend(
                            (m, integration.user_id) for m in new_meetings
                        )

                        logger.info(
                            f"[Scheduler] Fetched {len(new_meetings)} new meetings "
                            f"for {platform} (user {integration.user_id})"
                        )

                    except Exception as e:
                        logger.error(
                            f"[Scheduler] Polling error for {integration.platform}: {e}"
                        )

                # ── Step 2: Interleave round-robin across platforms ────────────
                # Build an ordered queue that alternates platforms so no single
                # platform dominates the scheduling window.
                platform_queues = {
                    p: list(items) for p, items in meetings_by_platform.items()
                }
                interleaved = []
                while any(platform_queues.values()):
                    for platform in list(platform_queues.keys()):
                        if platform_queues[platform]:
                            interleaved.append(platform_queues[platform].pop(0))

                # ── Step 3: Schedule in the interleaved order ─────────────────
                scheduled_count = 0
                for meeting, user_id in interleaved:
                    if self.store_and_schedule(meeting, user_id):
                        scheduled_count += 1

                logger.info(
                    f"[Scheduler] Fallback polling complete — "
                    f"scheduled {scheduled_count} new meetings across "
                    f"{list(meetings_by_platform.keys())}"
                )

        except Exception as e:
            logger.error(f"[Scheduler] _fallback_polling error: {e}")

    # ------------------------------------------------------------------
    # Microsoft subscription renewal
    # ------------------------------------------------------------------

    def schedule_microsoft_subscription_renewal(self):
        self.scheduler.add_job(
            func=self._renew_microsoft_subscriptions,
            trigger=IntervalTrigger(hours=24),
            id="microsoft_subscription_renewal",
            name="Renew Microsoft Graph Subscriptions",
            replace_existing=True,
        )
        logger.info("[Scheduler] Microsoft subscription renewal every 24 hours")

    def _renew_microsoft_subscriptions(self):
        try:

            from app.models.webhookModel import WebhookModel
            from app.services.tokenService import TokenService
            from app.controller.calendar.platform.microsoftCalendarService import (
                MicrosoftCalendarService,
            )

            with self.app.app_context():
                threshold = datetime.now(timezone.utc) + timedelta(hours=12)
                ms_webhooks = WebhookModel.query.filter_by(
                    platform="microsoft", is_active=True
                ).all()
                ms_service = MicrosoftCalendarService()

                for webhook in ms_webhooks:
                    try:
                        if not webhook.expiration:
                            continue
                        expiry = webhook.expiration
                        if expiry.tzinfo is None:
                            expiry = expiry.replace(tzinfo=timezone.utc)
                        if expiry > threshold:
                            continue

                        access_token = TokenService.get_valid_access_token(webhook)
                        success = ms_service.renew_webhook_channel(
                            access_token=access_token,
                            subscription_id=webhook.channel_id,
                        )
                        if success:
                            webhook.expiration = datetime.now(timezone.utc) + timedelta(
                                days=2
                            )
                            logger.info(
                                f"[Scheduler] Renewed MS subscription for user {webhook.user_id}"
                            )
                        else:
                            logger.error(
                                f"[Scheduler] Failed to renew MS subscription for user {webhook.user_id}"
                            )
                    except Exception as e:
                        logger.error(f"[Scheduler] MS renewal error: {e}")

                db.session.commit()

        except Exception as e:
            logger.error(f"[Scheduler] _renew_microsoft_subscriptions error: {e}")

    # ------------------------------------------------------------------
    # Job management helpers
    # ------------------------------------------------------------------

    def remove_job(self, job_id: str) -> bool:
        try:
            if self.scheduler and self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                return True
            return False
        except Exception as e:
            logger.error(f"[Scheduler] remove_job error: {e}")
            return False

    def get_scheduled_jobs(self) -> list:
        try:
            return self.scheduler.get_jobs() if self.scheduler else []
        except Exception as e:
            logger.error(f"[Scheduler] get_scheduled_jobs error: {e}")
            return []

    # ------------------------------------------------------------------
    # Time utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_ist_to_utc(ist_str: str) -> Optional[datetime]:
        try:
            ist_time = (
                datetime.fromisoformat(ist_str)
                if "T" in ist_str
                else datetime.strptime(ist_str, "%Y-%m-%d")
            )
            if ist_time.tzinfo is None:
                ist_time = pytz.timezone("Asia/Kolkata").localize(ist_time)
            return ist_time.astimezone(timezone.utc)
        except Exception as e:
            logger.error(f"[Scheduler] IST→UTC conversion failed for '{ist_str}': {e}")
            return None

    @staticmethod
    def _parse_ist_datetime(ist_str: str) -> Optional[datetime]:
        if not ist_str:
            return None
        try:
            return datetime.fromisoformat(ist_str)
        except ValueError:
            return None


# Global singleton
scheduler_service = SchedulerService()
