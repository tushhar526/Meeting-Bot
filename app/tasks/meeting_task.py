from app.celery_app import celery_app
from app.bot.base_meeting import BaseBot
from app.audio.audioModel import Audio, AudioFormat
from app.audio.audioService import get_audio_metadata
from app.meetings.meetingModel import BotStatus
from app.meetings.meetingUtils import update_bot
from app.core.database import get_db_session
from app.core.middlewares.global_logger import get_logger
from app.util.time_util import get_ist_now
from app.util.response_util.custom_exception import JoinDeniedError, WaitingRoomTimeoutError
import os

logger = get_logger("Meeting_Task")

# End-state statuses that should NOT be overwritten
_END_STATES = {BotStatus.DENIED, BotStatus.CANCELLED, BotStatus.COMPLETED, BotStatus.FAILED}


@celery_app.task(bind=True, name="meetings.start_bot")
def start_bot_task(
    self,
    meeting_id: int,
    meeting_url: str,
    original_path: str,
    processed_path: str,
    bot_alias: str,
):
    logger.info(f"Celery task started for meeting_id={meeting_id}")

    try:
        bot = BaseBot(
            meeting_id=meeting_id,
            meeting_url=meeting_url,
            original_path=original_path,
            processed_path=processed_path,
            bot_alias=bot_alias,
            update_bot=update_bot,
        )

        success, audio_timestamp = bot.run()

        if success and audio_timestamp:
            with get_db_session() as db:
                # Extract metadata from the original MP3 file
                metadata = get_audio_metadata(original_path) if os.path.exists(original_path) else None

                audio = Audio(
                    file_path=original_path,
                    processed_file_path=processed_path,
                    file_size_bytes=metadata.get("file_size_bytes") if metadata else None,
                    duration_seconds=metadata.get("duration_seconds") if metadata else None,
                    sample_rate=metadata.get("sample_rate") if metadata else None,
                    bit_rate=metadata.get("bitrate") if metadata else None,
                    channels=metadata.get("channel") if metadata else None,
                    recording_started_at=audio_timestamp["recording_started_at"],
                    recording_ended_at=audio_timestamp["recording_ended_at"],
                    created_at=audio_timestamp.get("created_at") or get_ist_now(),
                    meeting_id=meeting_id,
                )
                db.add(audio)

                # Update participant count in the meeting record
                from app.meetings.meetingModel import Meetings
                meeting = db.query(Meetings).filter(Meetings.id == meeting_id).first()
                if meeting and audio_timestamp.get("participant_count"):
                    meeting.participant_count = audio_timestamp["participant_count"]
                    logger.info(f"Updated participant_count for meeting_id={meeting_id} to {audio_timestamp['participant_count']}")

                db.commit()
                logger.info(f"Audio record created for meeting_id={meeting_id} with metadata: {metadata}")

            # Update bot status to COMPLETED after successful audio save (outside session to ensure commit is flushed)
            update_bot(meeting_id, bot_status=BotStatus.COMPLETED)
            logger.info(f"[COMPLETED DEBUG] Meeting {meeting_id} status set to COMPLETED - cache should be invalidated")

        else:
            # Bot failed but didn't raise exception
            # Check if status is already an end state (DENIED, CANCELLED, etc.) - don't overwrite
            with get_db_session() as db:
                from app.meetings.meetingModel import Meetings
                meeting = db.query(Meetings).filter(Meetings.id == meeting_id).first()
                current_status = meeting.bot_status if meeting else None

            if current_status in [s.value for s in _END_STATES]:
                logger.info(f"Bot run returned False but status is already '{current_status}' - not overwriting")
            else:
                logger.error(f"Bot run failed for meeting_id={meeting_id} without exception")
                update_bot(meeting_id, bot_status=BotStatus.FAILED, error_message="Bot run returned False")

    except JoinDeniedError as e:
        logger.error(f"Join denied for meeting_id={meeting_id}: {e}")
        update_bot(meeting_id, bot_status=BotStatus.DENIED, error_message="Bot was denied to join the meeting by the host")
        # Re-raise so Celery marks task as failed
        raise

    except WaitingRoomTimeoutError as e:
        logger.error(f"Waiting room timeout for meeting_id={meeting_id}: {e}")
        update_bot(meeting_id, bot_status=BotStatus.CANCELLED, error_message="Bot was not accepted inside the meeting within the span of 2 mins")
        # Re-raise so Celery marks task as failed
        raise

    except Exception as e:
        logger.error(f"Task failed for meeting_id={meeting_id}: {e}")
        # Check if status is already an end state before overwriting
        with get_db_session() as db:
            from app.meetings.meetingModel import Meetings
            meeting = db.query(Meetings).filter(Meetings.id == meeting_id).first()
            current_status = meeting.bot_status if meeting else None

        if current_status not in [s.value for s in _END_STATES]:
            update_bot(meeting_id, bot_status=BotStatus.FAILED, error_message="Bot couldn't join the meeting")
        else:
            logger.info(f"Exception occurred but status is already '{current_status}' - not overwriting with FAILED")
        raise
