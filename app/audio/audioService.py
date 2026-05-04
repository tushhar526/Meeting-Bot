import os
import mutagen
import subprocess
from app.util.response_util.response import SuccessResponse, ErrorResponse
from app.util.response_util.file_response import FileSuccessResponse
from app.util.response_util.custom_exception import NotFoundError
from .audioModel import Audio
from .audioSchema import AudioListResponse, AudioDetailResponse, AudioMetadataResponse
from sqlalchemy.orm import Session
from app.meetings.meetingModel import BotStatus, Meetings
from app.core.database import get_db_session
from app.core.middlewares.global_logger import get_logger


logger = get_logger("AUDIO_SERVICE")


def list_audio_service(db: Session, user_id: int):
    audios = (
        db.query(Audio)
        .join(Meetings, Audio.meeting_id == Meetings.id)
        .filter(
            Meetings.user_id == user_id,
            Meetings.bot_status == BotStatus.COMPLETED,
            Audio.is_deleted == False,
            Audio.file_path.isnot(None),
        )
        .all()
    )

    recordings_list = []
    for audio in audios:
        metadata = get_audio_metadata(audio.file_path)
        recording_response = AudioListResponse.from_audio_model(audio, metadata)
        recordings_list.append(recording_response.model_dump())

    return recordings_list


def get_audio_service(db: Session, audio_id: int, user_id: int):
    audio = (
        db.query(Audio)
        .join(Meetings, Audio.meeting_id == Meetings.id)
        .filter(
            Audio.id == audio_id,
            Meetings.user_id == user_id,
            Meetings.bot_status == BotStatus.COMPLETED,
            Audio.is_deleted == False,
            Audio.file_path.isnot(None),
        )
        .first()
    )

    if not audio:
        return None

    metadata = get_audio_metadata(audio.file_path)
    audio_response = AudioDetailResponse.from_audio_model(audio, metadata)

    return audio_response.model_dump()


def download_audio_service(db: Session, audio_id: int, user_id: int):
    """Download audio file as attachment"""
    logger.info(f"Audio download request for audio_id {audio_id} by user {user_id}")

    audio = (
        db.query(Audio)
        .join(Meetings, Audio.meeting_id == Meetings.id)
        .filter(
            Audio.id == audio_id,
            Meetings.user_id == user_id,
            Meetings.bot_status == BotStatus.COMPLETED,
            Audio.is_deleted == False,
            Audio.file_path.isnot(None),
        )
        .first()
    )

    if not audio:
        logger.warning(
            f"Download failed - audio not found: {audio_id} for user {user_id}"
        )
        return None

    # Fix path issues - normalize and handle container paths
    audio_path = audio.file_path

    # Remove duplicate /app/ prefix if it exists
    if audio_path.startswith("/app/app/"):
        audio_path = audio_path.replace("/app/app/", "/app/")

    # Handle relative paths - convert to absolute if needed
    if not audio_path.startswith("/"):
        audio_path = os.path.join(os.getcwd(), audio_path)

    logger.info(f"Downloading audio from: {audio_path}")

    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found at: {audio_path} for audio_id {audio_id}")
        return None

    logger.info(f"Audio download started for audio_id {audio_id}")

    # Create FileSuccessResponse with success headers for download
    filename = f"audio_{audio_id}_{os.path.basename(audio_path)}"

    response = FileSuccessResponse(
        path=audio_path,
        message="Audio downloaded successfully",
        media_type="audio/mpeg",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "public, max-age=3600",
        },
    )

    return response


def stream_audio_service(db: Session, audio_id: int, user_id: int):
    """Stream audio file for playback in frontend"""
    logger.info(f"Audio stream request for audio_id {audio_id} by user {user_id}")

    audio = (
        db.query(Audio)
        .join(Meetings, Audio.meeting_id == Meetings.id)
        .filter(
            Audio.id == audio_id,
            Meetings.user_id == user_id,
            Meetings.bot_status == BotStatus.COMPLETED,
            Audio.is_deleted == False,
            Audio.file_path.isnot(None),
        )
        .first()
    )

    if not audio:
        logger.warning(
            f"Stream failed - audio not found: {audio_id} for user {user_id}"
        )
        return None

    # Fix path issues - normalize and handle container paths
    audio_path = audio.file_path

    # Remove duplicate /app/ prefix if it exists
    if audio_path.startswith("/app/app/"):
        audio_path = audio_path.replace("/app/app/", "/app/")

    # Handle relative paths - convert to absolute if needed
    if not audio_path.startswith("/"):
        audio_path = os.path.join(os.getcwd(), audio_path)

    logger.info(f"Streaming audio from: {audio_path}")

    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found at: {audio_path} for audio_id {audio_id}")
        raise NotFoundError("Audio file not found")

    logger.info(f"Audio streaming started for audio_id {audio_id}")

    # Get audio metadata
    metadata = get_audio_metadata(audio_path)

    # Prepare headers including metadata
    extra_headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
    }

    # Add metadata to response headers
    if metadata:
        extra_headers["X-Audio-Duration"] = str(metadata["duration_seconds"])
        extra_headers["X-Audio-Duration-Formatted"] = metadata["duration_formatted"]
        extra_headers["X-Audio-File-Size"] = str(metadata["file_size_bytes"])
        extra_headers["X-Audio-File-Size-MB"] = str(metadata["file_size_mb"])

        # Also expose these headers in CORS
        extra_headers["Access-Control-Expose-Headers"] = ", ".join(
            [
                "Content-Range",
                "Accept-Ranges",
                "Content-Length",
                "X-Audio-Duration",
                "X-Audio-Duration-Formatted",
                "X-Audio-File-Size",
                "X-Audio-File-Size-MB",
            ]
        )

    # Create FileSuccessResponse with success headers for streaming
    response = FileSuccessResponse(
        path=audio_path,
        message="Audio streamed successfully",
        data=metadata,  # Include full metadata in X-Data header
        media_type="audio/mpeg",
        filename=os.path.basename(audio_path),
        headers=extra_headers,
    )

    return response


def update_audio(audio_id, **fields):
    with get_db_session as db:
        audio = db.query(Audio).filter_by()
    pass


def get_audio_metadata(file_path: str):
    """Get metadata of the audio files"""
    try:
        if not os.path.exists(file_path):
            return None

        # getting audio file size in mb
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = round((file_size_bytes / (1024 * 1024)), 2)

        # audio duration in minutes
        duration_seconds = 0
        try:
            audio = mutagen.File(file_path)
            if audio is not None:
                duration_seconds = audio.info.length
        except Exception as e:
            logger.warning(f"Could not extract duration with mutagen: {e}")

        if duration_seconds > 0:
            duration_minutes = round(duration_seconds / 60, 2)
            duration_str = f"{duration_minutes} min"
        else:
            duration_str = "Unknown"

        # returning the calculated values
        return {
            "duration_seconds": duration_seconds,
            "duration_formatted": duration_str,
            "file_size_bytes": file_size_bytes,
            "file_size_mb": file_size_mb,
            "bitrate": audio.info.bitrate,
            "sample_rate": audio.info.sample_rate,
            "channel": audio.info.channels,
        }

    except Exception as e:
        logger.error(f"Error getting audio metadata: {e}")
        return None
