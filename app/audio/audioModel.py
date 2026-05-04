from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
    Enum as SqlEnum,
)
from app.core.database import Base
from enum import Enum
from datetime import datetime


class AudioFormat(str, Enum):
    MP3 = "mp3"
    WAV = "wav"
    OPUS = "opus"
    OGG = "ogg"
    FLAC = "flac"
    M4A = "m4a"


class StorageProvider(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"


class Audio(Base):
    __tablename__ = "audio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    file_path: Mapped[str] = mapped_column(String, nullable=False)
    processed_file_path: Mapped[str] = mapped_column(String, nullable=False)
    storage_provider: Mapped[str] = mapped_column(
        SqlEnum(StorageProvider), nullable=False, default=StorageProvider.LOCAL
    )

    # File properties
    format: Mapped[str] = mapped_column(SqlEnum(AudioFormat), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)

    # Audio technical specs
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=True)
    channels: Mapped[int] = mapped_column(Integer, nullable=True, default=1)
    bit_rate: Mapped[int] = mapped_column(Integer, nullable=True)

    # Recording window (the actual time the bot was recording, within the meeting)
    recording_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    recording_ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Foreign key & relationships
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    meeting = relationship("Meetings", back_populates="audios")
