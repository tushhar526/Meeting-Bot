from typing import Any
from app.meetings.meetingModel import Meetings
from app.users.userModel import Users  # Import to ensure mapper is initialized
from app.users.usersService import invalidate_analytics_cache, get_user_analytics_service
from app.core.database import get_db_session
from app.core.middlewares.global_logger import get_logger

logger = get_logger("MEETING_UTILS")


def detect_platform_from_url(url: str) -> str:
    """Detect meeting platform from URL and return valid enum value."""
    url_lower = url.lower()
    if "meet.google.com" in url_lower:
        return "google meet"
    elif "zoom.us" in url_lower or "zoom.com" in url_lower:
        return "zoom"
    elif "teams.microsoft.com" in url_lower or "teams.live.com" in url_lower:
        return "microsoft teams"
    return "google meet"  # default


def update_bot(id: int, **fields: Any):
    with get_db_session() as db:
        bot = db.query(Meetings).filter(Meetings.id == id).first()

        if not bot:
            logger.warning(f"update_bot: Meeting {id} not found")
            return None

        old_status = bot.bot_status
        for key, value in fields.items():
            if hasattr(bot, key):
                if callable(value):
                    setattr(bot, key, value(getattr(bot, key)))
                else:
                    setattr(bot, key, value)
            else:
                raise ValueError(f"Invalid field: {key}")

        db.commit()

        # Log status change
        new_status = bot.bot_status
        if old_status != new_status:
            logger.info(f"Meeting {id} status changed: {old_status} -> {new_status}")

        # Invalidate cache AFTER commit to prevent race conditions
        # This ensures any concurrent analytics requests will see the committed data
        invalidate_analytics_cache(bot.user_id)
        logger.info(f"[CACHE] Analytics cache invalidated for user {bot.user_id} after meeting {id} update")

        # Warm the cache with fresh data immediately to prevent stale data from being re-cached
        try:
            fresh_analytics = get_user_analytics_service(db, bot.user_id)
            logger.info(f"[CACHE] Analytics cache warmed with fresh data for user {bot.user_id}: {fresh_analytics.get('completed_meetings', 0)} completed meetings")
        except Exception as e:
            logger.warning(f"[CACHE] Failed to warm analytics cache for user {bot.user_id}: {e}")

        return bot
