from sqlalchemy.orm import Session
from .audioService import (
    list_audio_service,
    get_audio_service,
    download_audio_service,
    stream_audio_service,
)


def list_audio(db: Session, user_id: int):
    return list_audio_service(db, user_id)


def get_audio(db: Session, audio_id: int, user_id: int):
    return get_audio_service(db, audio_id, user_id)


def download_audio(db: Session, audio_id: int, user_id: int):
    return download_audio_service(db, audio_id, user_id)


def stream_audio(db: Session, audio_id: int, user_id: int):
    return stream_audio_service(db, audio_id, user_id)
