from fastapi import APIRouter, Depends
from app.core.middlewares.jwt_authenticator import get_current_user_id
from app.core.database import get_db
from app.util.response_util.response import SuccessResponse
from app.util.response_util.file_response import FileSuccessResponse
from .audioController import list_audio, get_audio, download_audio, stream_audio
from sqlalchemy.orm import Session

audiorouter = APIRouter(prefix="/audio", tags=["Audio"])


@audiorouter.get("/list")
def list_audio_route(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    audio_list = list_audio(db, user_id)
    return SuccessResponse(message="Audio list retrieved successfully", data=audio_list)


@audiorouter.get("/{audio_id}")
def get_audio_route(
    audio_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    audio_file = get_audio(db, audio_id, user_id)
    return SuccessResponse(message="Audio retrieved successfully", data=audio_file)


@audiorouter.get("/download/{audio_id}")
def download_audio_route(
    audio_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
) -> FileSuccessResponse:
    """Download audio file as attachment with success headers."""
    return download_audio(db, audio_id, user_id)


@audiorouter.get("/stream/{audio_id}")
def stream_audio_route(
    audio_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
) -> FileSuccessResponse:
    """Stream audio file with success headers for frontend playback."""
    return stream_audio(db, audio_id, user_id)
