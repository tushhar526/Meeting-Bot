from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .meetingSchema import CreateBotRequest, MeetingResponse, BotStatusResponse
from app.util.response_util.custom_exception import NotFoundError
from app.util.time_util import get_ist_now
from app.tasks.meeting_task import start_bot_task
from .meetingModel import Meetings
from app.users.userModel import Users
from app.users.usersService import invalidate_analytics_cache
from app.core.middlewares.global_logger import get_logger
from app.meetings.meetingUtils import update_bot, detect_platform_from_url

logger = get_logger("MEETING")


def create_bot_service(db: Session, data: CreateBotRequest, user_id: int):
    logger.info(f"Entered Meeting service pipeline for user = {user_id}")
    try:
        url_str = str(data.meeting_url)
        platform = detect_platform_from_url(url_str)

        existing = (
            db.query(Meetings)
            .filter(Meetings.url == url_str, Meetings.user_id == user_id)
            .order_by(Meetings.created_at.desc())
            .first()
        )

        if existing:
            logger.info(f"Meeting with url already exists. Storing the recurring id")
            recurring_id = existing.recurring_meeting_id or str(existing.id)
        else:
            recurring_id = None

        meeting = Meetings(
            title=data.title,
            url=url_str,
            user_id=user_id,
            platform=platform,
            recurring_meeting_id=recurring_id,
            created_at=get_ist_now(),
        )

        db.add(meeting)
        db.commit()

        # Invalidate user analytics cache when new meeting is created
        invalidate_analytics_cache(user_id)

        user = db.query(Users).filter_by(id=user_id).first()

        original_path = f"app/recordings/{meeting.retry_count}_{meeting.id}_{user.username}_original_audio.mp3"
        processed_path = f"app/processed/{meeting.retry_count}_{meeting.id}_{user.username}_processed_audio.wav"

        start_bot_task.delay(
            meeting_id=meeting.id,
            meeting_url=meeting.url,
            original_path=original_path,
            processed_path=processed_path,
            bot_alias=user.bot_alias,
        )

        logger.info(f"Meeting instance created successfully")

        return meeting

    except IntegrityError:
        db.rollback()
        logger.warning("Integrity error while creating meeting")
        raise

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while creating meeting: {e}")
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {e}")
        raise


def get_bot_status_service(db: Session, meeting_id: int, user_id: int):
    try:
        meeting = db.query(Meetings).filter_by(id=meeting_id, user_id=user_id).first()

        if not meeting:
            raise NotFoundError("No such Meeting found")

        # Define end states (must match BotStatus enum values)
        end_states = ["denied", "completed", "failed"]

        # If status is an end state, return full meeting data
        if meeting.bot_status in end_states:
            meeting_response = MeetingResponse(
                id=meeting.id,
                meeting_url=meeting.url,
                title=meeting.title,
                status=meeting.bot_status,
                platform=meeting.platform,
                created_at=meeting.created_at,
                scheduled_time=meeting.scheduled_time,
                started_at=meeting.started_at,
                ended_at=meeting.ended_at,
                bot_join_time=meeting.bot_join_time,
                bot_leave_time=meeting.bot_leave_time,
                waiting_room_entered_at=meeting.waiting_room_entered_at,
                participant_count=getattr(meeting, 'participant_count', None),
                error_message=meeting.error_message,
                retry_count=meeting.retry_count,
            )
            return meeting_response

        # For non-end states, return lightweight status response
        return BotStatusResponse(
            status=meeting.bot_status,
            platform=meeting.platform,
            title=meeting.title,
            created_at=meeting.created_at,
            started_at=meeting.started_at,
        )
    except Exception as e:
        logger.error(f"Error in getting the bot status due to {str(e)}")
        raise


