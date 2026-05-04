from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, ForeignKey, Enum as SqlEnum
from app.core.database import Base
from enum import Enum
from datetime import datetime


class BotStatus(str, Enum):
    REGISTERED = "registered"
    SCHEDULED = "scheduled"
    WAITING_ROOM = "waiting room"
    DENIED = "denied"
    MEETING_JOINED = "meeting joined"
    RECORDING_STARTED = "recording started"
    GRACE_PERIOD = "grace period"
    MEETING_ENDED = "meeting ended"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class MeetingPlatform(str, Enum):
    GOOGLE_MEET = "google meet"
    MICROSOFT_TEAMS = "microsoft teams"
    ZOOM = "zoom"


class  Meetings(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    bot_status: Mapped[str] = mapped_column(
        SqlEnum(BotStatus), nullable=False, default=BotStatus.REGISTERED
    )
    platform: Mapped[str] = mapped_column(SqlEnum(MeetingPlatform), nullable=False)

    # Timestamps (timezone-aware)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    waiting_room_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    bot_join_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    bot_leave_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Meeting metadata
    participant_count: Mapped[int] = mapped_column(Integer, nullable=True)
    recurring_meeting_id: Mapped[str] = mapped_column(String, nullable=True)

    # Bot reliability fields
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str] = mapped_column(String, nullable=True)

    # Foreign keys & relationships

    # user table foreign key
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user = relationship("Users", back_populates="meetings")

    audios = relationship("Audio", back_populates="meeting")
