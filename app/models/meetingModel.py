from sqlalchemy import Column, DateTime, Integer, String, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.helper import get_ist_now
from app import Base
from enum import Enum


class MeetingStatus(str, Enum):
    REGISTERED = "registered"
    SCHEDULED = "scheduled"
    BOT_CREATED = "bot created"
    IN_WAITING_ROOM = "in waiting room"
    MEETING_JOINED = "meeting joined"
    RECORDING_STARTED = "recording started"
    COMPLETED = "completed"
    FAILED = "failed"


class Meetings(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    url = Column(String(100), unique=True, nullable=False)
    status = Column(
        SQLEnum(MeetingStatus), default=MeetingStatus.REGISTERED, nullable=False
    )
    platform = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=get_ist_now())
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)

    # user info using Foreign key relationship
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="meetings")
