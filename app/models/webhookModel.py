from app.extension import db
from sqlalchemy import String, Integer, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import pytz


def get_ist_now():
    """Get current datetime in Indian Standard Time (naive for database storage)"""
    ist = pytz.timezone("Asia/Kolkata")
    utc_now = datetime.now(timezone.utc)
    ist_now = utc_now.astimezone(ist)
    return ist_now.replace(tzinfo=None)


class WebhookModel(db.Model):
    __tablename__ = "webhooks"

    webhook_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    webhook_url: Mapped[str] = mapped_column(String, nullable=False)
    webhook_secret: Mapped[str] = mapped_column(String, nullable=True)
    event_types: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON string of event types
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_ist_now())
    last_triggered: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Calendar specific fields
    platform: Mapped[str] = mapped_column(String, nullable=False, default="google")
    calendar_email: Mapped[str] = mapped_column(String, nullable=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    redirect_uri: Mapped[str] = mapped_column(
        String, nullable=True
    )
    auto_create_jobs: Mapped[bool] = mapped_column(Boolean, default=True)
    check_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    meeting_start_buffer_minutes: Mapped[int] = mapped_column(Integer, default=5)

    # Google webhook channel fields
    channel_id: Mapped[str] = mapped_column(
        String, nullable=True
    )  # Google channel ID (also used for Zoom/Microsoft mapping)
    resource_id: Mapped[str] = mapped_column(
        String, nullable=True
    )  # Google resource ID
    expiration: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )  # Channel expiration

    # Zoom webhook fields
    webhook_platform_id: Mapped[str] = mapped_column(
        String, nullable=True
    )  # Zoom webhook_id / Microsoft subscription_id
    webhook_events: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON string of events (Zoom)
    webhook_active: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # Webhook active status (Zoom)

    # Microsoft Graph subscription fields
    notification_url: Mapped[str] = mapped_column(
        String, nullable=True
    )  # Microsoft notification URL
    change_type: Mapped[str] = mapped_column(
        String, nullable=True
    )  # Microsoft change types
    subscription_resource: Mapped[str] = mapped_column(
        String, nullable=True
    )  # Microsoft resource (me/events, etc.)
    client_state: Mapped[str] = mapped_column(
        String, nullable=True
    )  # Microsoft client state

    def save(self):
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
            "id": self.webhook_id,
            "user_id": self.user_id,
            "webhook_url": self.webhook_url,
            "event_types": self.event_types,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_triggered": (
                self.last_triggered.isoformat() if self.last_triggered else None
            ),
            "platform": self.platform,
            "calendar_email": self.calendar_email,
            "auto_create_jobs": self.auto_create_jobs,
            "check_interval_minutes": self.check_interval_minutes,
            "meeting_start_buffer_minutes": self.meeting_start_buffer_minutes,
        }
