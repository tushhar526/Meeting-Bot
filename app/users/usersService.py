from app.core.redis import redis_client
import json
from datetime import datetime, timedelta
from typing import Any, Dict
from app.meetings.meetingModel import Meetings, BotStatus
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.core.config import setting
from app.util.time_util import get_ist_now
from app.core.middlewares.global_logger import get_logger
from app.users.usersSchema import RecentMeetingData

logger = get_logger("USER_SERVICE")


def get_user_analytics_service(db: Session, user_id: int) -> Dict[str, Any]:
    logger.info(f"User analytics request for user {user_id}")

    # DEBUG: Bypass cache to check if DB has stale data
    # Try cache first
    # cached_result = _get_analytics_from_cache(user_id)
    # if cached_result:
    #     logger.info(f"Serving analytics from cache for user {user_id}")
    #     return cached_result

    logger.info(f"[ANALYTICS DEBUG] Fetching directly from DB for user {user_id}")

    try:
        # 1. Total meetings count (single efficient query)
        total_meetings = db.query(Meetings).filter(Meetings.user_id == user_id).count()

        # 2. Completed meetings with duration data
        # Using single query to get all needed data
        completed_meetings_query = (
            db.query(Meetings)
            .filter(
                Meetings.user_id == user_id,
                Meetings.bot_status == BotStatus.COMPLETED,
                Meetings.started_at.isnot(None),
                Meetings.ended_at.isnot(None),
            )
            .all()
        )

        # Calculate average duration in Python (more efficient than multiple SQL queries)
        total_duration_seconds = 0.0
        completed_count = 0

        for meeting in completed_meetings_query:
            duration = meeting.ended_at - meeting.started_at
            total_duration_seconds += duration.total_seconds()
            completed_count += 1

        # Debug logging for completed meetings
        logger.info(
            f"User {user_id}: Found {completed_count} completed meetings out of {total_meetings} total"
        )
        if completed_meetings_query:
            meeting_ids = [m.id for m in completed_meetings_query]
            logger.info(f"Completed meeting IDs: {meeting_ids}")

        avg_duration_hours = 0.0
        if completed_count > 0:
            avg_duration_hours = round(
                total_duration_seconds / (completed_count * 3600), 2
            )

        # 3. Time-based analytics
        now = get_ist_now()

        # Week start (Monday)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Month start
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # This week's meetings
        this_week_meetings = (
            db.query(Meetings)
            .filter(Meetings.user_id == user_id, Meetings.created_at >= week_start)
            .count()
        )

        # This month's meetings
        this_month_meetings = (
            db.query(Meetings)
            .filter(Meetings.user_id == user_id, Meetings.created_at >= month_start)
            .count()
        )

        # 4. Meetings by day of week (database-level aggregation)
        meetings_by_day_result = (
            db.query(
                extract("dow", Meetings.created_at).label("day_of_week"),
                func.count(Meetings.id).label("count"),
            )
            .filter(Meetings.user_id == user_id)
            .group_by(extract("dow", Meetings.created_at))
            .all()
        )

        # Convert to readable format (0=Sunday, 1=Monday, etc.)
        day_names = [
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ]
        meetings_by_day = {day: 0 for day in day_names}

        for day_num, count in meetings_by_day_result:
            day_name = day_names[int(day_num)]
            meetings_by_day[day_name] = count

        # 5. Platform distribution
        platform_stats = (
            db.query(Meetings.platform, func.count(Meetings.id).label("count"))
            .filter(Meetings.user_id == user_id)
            .group_by(Meetings.platform)
            .all()
        )

        platform_distribution = {platform: count for platform, count in platform_stats}

        # 6. Recent meetings (last 10) - single efficient query
        recent_meetings = (
            db.query(Meetings)
            .filter(Meetings.user_id == user_id)
            .order_by(Meetings.created_at.desc())
            .limit(10)
            .all()
        )

        recent_meetings_data = []
        for meeting in recent_meetings:
            duration_hours = _calculate_meeting_duration(meeting)

            recent_meetings_data.append(
                RecentMeetingData(
                    meeting_id=meeting.id,
                    meeting_url=meeting.url,
                    platform=meeting.platform.value if hasattr(meeting.platform, 'value') else meeting.platform,
                    status=meeting.bot_status.value if hasattr(meeting.bot_status, 'value') else meeting.bot_status,
                    title=meeting.title,
                    participant_count=meeting.participant_count or 0,
                    created_at=meeting.created_at,
                    started_at=meeting.started_at,
                    ended_at=meeting.ended_at,
                    duration_hours=duration_hours,
                )
            )

        # Build response
        result = {
            "total_meetings": total_meetings,
            "completed_meetings": completed_count,
            "average_duration_hours": avg_duration_hours,
            "this_week_meetings": this_week_meetings,
            "this_month_meetings": this_month_meetings,
            "meetings_by_day": meetings_by_day,
            "platform_distribution": platform_distribution,
            "recent_meetings": [m.model_dump() for m in recent_meetings_data],
            "analytics_period": {
                "week_start": week_start.isoformat(),
                "month_start": month_start.isoformat(),
                "current_date": now.isoformat(),
            },
            "cached": False,
            "cached_at": None,
        }

        # DEBUG: Skip cache storage
        # Store in cache
        # _set_analytics_cache(user_id, result)

        logger.info(f"[ANALYTICS DEBUG] Analytics computed from DB for user {user_id} (not cached)")
        return result

    except Exception as e:
        logger.error(f"Error generating analytics for user {user_id}: {e}")
        raise


def _get_cache_key(user_id: int) -> str:
    """Generate cache key for user analytics"""
    return f"user_analytics:{user_id}"


def _serialize_datetime(obj: Any) -> str:
    """Helper to serialize datetime objects for JSON"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _get_analytics_from_cache(user_id: int) -> Dict[str, Any] | None:
    """Get analytics from Redis cache if available (sync)"""
    try:
        cache_key = _get_cache_key(user_id)
        data = redis_client.get(cache_key)
        if data:
            cached_data = json.loads(data)
            logger.info(
                f"[ANALYTICS DEBUG] Cache HIT for user {user_id}: completed_meetings={cached_data.get('completed_meetings', 'N/A')}"
            )
            return cached_data
        else:
            logger.info(f"[ANALYTICS DEBUG] Cache MISS for user {user_id}")
    except Exception as e:
        logger.warning(f"Cache read error: {e}")

    return None


def _set_analytics_cache(user_id: int, data: Dict[str, Any]) -> None:
    """Store analytics in Redis cache (sync)"""
    try:
        cache_key = _get_cache_key(user_id)
        # Add cache metadata
        data["cached"] = True
        data["cached_at"] = datetime.utcnow().isoformat()

        # Synchronous Redis call
        redis_client.setex(
            cache_key,
            setting.REDIS_DATA_EXPIRE,
            json.dumps(data, default=_serialize_datetime),
        )
        logger.info(
            f"[ANALYTICS DEBUG] Cache SET for user {user_id}: completed_meetings={data.get('completed_meetings', 'N/A')}"
        )
    except Exception as e:
        logger.warning(f"[ANALYTICS DEBUG] Cache write error: {e}")


def _invalidate_user_cache(user_id: int) -> None:
    """Invalidate user analytics cache (call when meetings change)"""
    try:
        cache_key = _get_cache_key(user_id)
        result = redis_client.delete(cache_key)
        logger.info(
            f"[ANALYTICS DEBUG] Cache invalidated for user {user_id}, deleted keys: {result}"
        )
    except Exception as e:
        logger.warning(
            f"[ANALYTICS DEBUG] Cache invalidation failed for user {user_id}: {e}"
        )


def invalidate_analytics_cache(user_id: int) -> None:
    """
    Call this function when a meeting is created/updated/deleted
    to invalidate the user's analytics cache.
    """
    _invalidate_user_cache(user_id)


def _calculate_meeting_duration(meeting: Meetings) -> float | None:
    """Calculate meeting duration in hours"""
    if meeting.started_at and meeting.ended_at:
        duration = meeting.ended_at - meeting.started_at
        return round(duration.total_seconds() / 3600, 2)
    return None


def get_meeting_trends_service(
    db: Session, user_id: int, days: int = 30
) -> Dict[str, Any]:
    """Get meeting trends over specified number of days"""
    logger.info(f"Meeting trends request for user {user_id}, period: {days} days")

    try:
        end_date = get_ist_now()
        start_date = end_date - timedelta(days=days)

        # Daily meeting counts using created_at field
        daily_meetings = (
            db.query(
                func.date(Meetings.created_at).label("date"),
                func.count(Meetings.id).label("count"),
            )
            .filter(Meetings.user_id == user_id)
            .filter(Meetings.created_at >= start_date, Meetings.created_at <= end_date)
            .group_by(func.date(Meetings.created_at))
            .order_by("date")
            .all()
        )

        # Convert to dict with all dates (fill missing dates with 0)
        trends_data: Dict[str, int] = {}
        current_date = start_date.date()

        while current_date <= end_date.date():
            trends_data[current_date.isoformat()] = 0
            current_date += timedelta(days=1)

        # Fill in actual counts
        for date_obj, count in daily_meetings:
            date_str = (
                date_obj.isoformat()
                if hasattr(date_obj, "isoformat")
                else str(date_obj)
            )
            trends_data[date_str] = count

        total_meetings = sum(trends_data.values())
        average_per_day = round(total_meetings / days, 2) if days > 0 else 0

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily_trends": trends_data,
            "total_meetings_in_period": total_meetings,
            "average_per_day": average_per_day,
        }
    except Exception as e:
        logger.error(f"Error generating meeting trends for user {user_id}: {e}")
        raise
