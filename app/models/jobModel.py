from app.extension import db
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime


class JobModel(db.Model):
    __tablename__ = "jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_url: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    audio_path: Mapped[str] = mapped_column(String, nullable=True)
    transcript_path: Mapped[str] = mapped_column(String, nullable=True)

    @property
    def to_json(self):
        return {
            "id": self.job_id,
            "meeting_url": self.job_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
            # 'started_at': self.started_at.isoformat() if self.started_at else None,
            # 'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            # "audio_path": self.audio_path,
            # "transcript_path": self.transcript_path,
            # 'error_message': self.error_message
        }
