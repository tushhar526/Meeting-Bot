from app.extension import db
from sqlalchemy import String, DateTime, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone, timedelta


class UserIntegration(db.Model):
    """Model to store user calendar integrations"""

    __tablename__ = "user_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id"), nullable=False
    )

    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    account_email: Mapped[str] = mapped_column(String(255), nullable=True)

    access_token: Mapped[str] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship back to User
    user = relationship("userModel", backref="integrations")

    def to_dict(self):
        """Convert integration to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "platform": self.platform,
            "account_email": self.account_email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    def update_tokens(
        self, access_token: str, refresh_token: str, expires_in: int = None
    ):
        """Update tokens and expiry"""
        self.access_token = access_token
        self.refresh_token = refresh_token
        if expires_in:
            self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        self.updated_at = datetime.now(timezone.utc)

    def is_expired(self):
        """Check if tokens are expired"""
        if not self.expires_at:
            return False
        
        # Handle both naive and aware datetimes
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        
        # If expires_at is naive, assume UTC
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        return now > expires_at

    def deactivate(self):
        """Deactivate integration"""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def get_by_user_and_platform(cls, user_id: int, platform: str):
        """Get integration by user and platform"""
        return cls.query.filter_by(
            user_id=user_id, platform=platform, is_active=True
        ).first()

    @classmethod
    def get_all_by_user(cls, user_id: int):
        """Get all integrations for a user"""
        return cls.query.filter_by(user_id=user_id, is_active=True).all()

    @classmethod
    def get_active_integrations(cls, user_id: int):
        """Get active integrations for a user"""
        return cls.query.filter_by(user_id=user_id, is_active=True).all()
