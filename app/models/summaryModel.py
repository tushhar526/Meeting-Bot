from app.extension import db
from sqlalchemy import Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from datetime import datetime
from app.helper import get_ist_now, format_ist_datetime


class SummaryStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SummaryModel(db.Model):
    __tablename__ = "summary"

    summary_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    transcription_id: Mapped[int] = mapped_column(
        ForeignKey("transcriptions.transcription_id")
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.job_id"))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_ist_now)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    file_path: Mapped[str] = mapped_column(String, nullable=True)

    status: Mapped[str] = mapped_column(String, default="pending")

    transcription = relationship("TranscriptionsModel", back_populates="summary")
    job = relationship("JobModel", back_populates="summary")

    @property
    def to_json(self) -> dict:
        return {
            "summary_id": self.summary_id,
            "transcription_id": self.transcription_id,
            "job_id": self.job_id,
            "status": self.status,
            "file_path": self.file_path,
            "created_at": self.created_at,
            "created_at_formatted": format_ist_datetime(self.created_at),
        }
