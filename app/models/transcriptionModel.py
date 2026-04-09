from app.extension import db
from app.helper import get_ist_now, format_ist_datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Float, Boolean, DateTime, ForeignKey
from datetime import datetime
from enum import Enum


class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionsModel(db.Model):
    __tablename__ = "transcriptions"

    transcription_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.job_id"))

    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[float] = mapped_column(Float, nullable=True)

    transcription_engine: Mapped[str] = mapped_column(String, default="GPT Whisper")
    language: Mapped[str] = mapped_column(String(10), default="en")

    word_count: Mapped[int] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_ist_now)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    job = relationship("JobModel", back_populates="transcript")
    user = relationship("userModel", back_populates="transcriptions")

    summary = relationship("SummaryModel", back_populates="transcription")

    @property
    def to_json(self):
        return {
            "id": self.transcription_id,
            "word_count": self.word_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "platform": self.job.platform if self.job else None,
            "created_at_formatted": format_ist_datetime(self.created_at),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "started_at_formatted": format_ist_datetime(self.started_at),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "completed_at_formatted": format_ist_datetime(self.completed_at),
        }
