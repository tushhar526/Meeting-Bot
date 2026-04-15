from sqlalchemy import Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core import password_hasher, Base
from app.util import get_ist_now
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
    deleted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_ist_now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=get_ist_now(),
        onupdate=get_ist_now(),
    )

    @classmethod
    def create_user(cls, user_data):
        hashed_pass = password_hasher.hash(user_data.password)

        return cls(
            username=user_data.username, email=user_data.email, password=hashed_pass
        )
