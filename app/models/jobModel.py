from app.extension import db
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import pytz


def get_ist_now():
    """Get current datetime in Indian Standard Time (naive for database storage)"""
    ist = pytz.timezone('Asia/Kolkata')
    utc_now = datetime.utcnow()
    ist_now = utc_now.replace(tzinfo=pytz.UTC).astimezone(ist)
    # Return naive datetime (without timezone) for database storage
    return ist_now.replace(tzinfo=None)


def format_ist_datetime(dt):
    """Format datetime in readable IST format for frontend"""
    if dt is None:
        return None
    # If datetime is naive (no timezone), assume it's already in IST
    if dt.tzinfo is None:
        ist = pytz.timezone('Asia/Kolkata')
        dt = ist.localize(dt)
    return dt.strftime('%d-%m-%Y %I:%M %p')


class JobModel(db.Model):
    __tablename__ = "jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_url: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="Registered")
    platform: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_ist_now)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    audio_path: Mapped[str] = mapped_column(String, nullable=True)
    # transcript_path: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    user = relationship("userModel", back_populates="jobs")

    def save(self):
        db.session.add(self)
        db.session.commit()

    @property
    def to_json(self):
        return {
            "id": self.job_id,
            "meeting_url": self.job_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_at_formatted": format_ist_datetime(self.created_at),
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "started_at_formatted": format_ist_datetime(self.started_at),
            # 'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            # "audio_path": self.audio_path,
            # "transcript_path": self.transcript_path,
            # 'error_message': self.error_message
        }