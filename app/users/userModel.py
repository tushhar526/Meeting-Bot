from sqlalchemy import Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base
from app.util.time_util import get_ist_now
from enum import Enum
from datetime import datetime, timezone


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    organization_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        SQLEnum(UserRole), nullable=False, default=UserRole.ADMIN
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # Soft delete flag
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_ist_now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_ist_now(),
        onupdate=get_ist_now(),
    )

    # meeting_related
    meetings = relationship("Meetings", back_populates="user")
    bot_alias: Mapped[str] = mapped_column(String, nullable=False)
    total_meetings: Mapped[int] = mapped_column(Integer, default=0)
