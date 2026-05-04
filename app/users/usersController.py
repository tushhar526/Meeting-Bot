from .usersService import get_user_analytics_service, get_meeting_trends_service
from sqlalchemy.orm import Session
from typing import Dict, Any


def get_user_analytics(db: Session, user_id: int) -> Dict[str, Any]:
    return get_user_analytics_service(db, user_id)


def get_meeting_trends(db: Session, user_id: int, days: int) -> Dict[str, Any]:
    return get_meeting_trends_service(db, user_id, days)
