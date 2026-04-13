from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app import Base
from app.helper import get_ist_now
from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)
    password = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    organization = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.ADMIN)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, get_ist_now())
    updated_at = Column(
        DateTime,
        default=get_ist_now(),
        onupdate=get_ist_now(),
    )

    # meetings for this user
    meetings = relationship("Meetings", back_populates="user")
    total_meetings = Column(Integer, default=0)
