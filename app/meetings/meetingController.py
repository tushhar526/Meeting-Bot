from sqlalchemy.orm import Session
from .meetingService import create_bot_service, get_bot_status_service
from .meetingSchema import CreateBotRequest


def create_bot(db: Session, data: CreateBotRequest, user_id: int):
    return create_bot_service(db, user_id, data)


def get_bot_status(db: Session, meeting_id: int, user_id: int):
    return get_bot_status_service(db, meeting_id, user_id)
