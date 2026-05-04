from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime
from app.util.time_util import format_ist_datetime


class AudioListResponse(BaseModel):
    id: int
    name: str
    meeting_link: str
    platform: str
    status: str
    created_at: Optional[datetime] = None
    created_at_formatted: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    scheduled_time_formatted: Optional[str] = None
    duration: str
    file_size: float

    @classmethod
    def from_audio_model(cls, audio, metadata: Optional[dict] = None) -> "AudioListResponse":
        """Create AudioListResponse from Audio model and metadata"""
        return cls(
            id=audio.id,
            name=audio.file_path.split('/')[-1] if audio.file_path else "Unknown",
            meeting_link=audio.meeting.url,
            platform=audio.meeting.platform.value,
            status=audio.meeting.bot_status.value,
            created_at=audio.created_at,
            scheduled_time=audio.meeting.scheduled_time,
            duration=metadata.get("duration_formatted", "Unknown") if metadata else "Unknown",
            file_size=metadata.get("file_size_mb", 0) if metadata else 0,
        )

    @model_validator(mode="after")
    def format_dates(self) -> "AudioListResponse":
        self.created_at_formatted = format_ist_datetime(self.created_at)
        self.scheduled_time_formatted = format_ist_datetime(self.scheduled_time)
        return self


class AudioMetadataResponse(BaseModel):
    duration_seconds: float
    duration_formatted: str
    file_size_bytes: int
    file_size_mb: float
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channel: Optional[int] = None


class AudioDetailResponse(BaseModel):
    id: int
    file_path: str
    processed_file_path: str
    storage_provider: str
    format: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bit_rate: Optional[int] = None
    recording_started_at: Optional[datetime] = None
    recording_ended_at: Optional[datetime] = None
    created_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    meeting_id: int
    metadata: Optional[AudioMetadataResponse] = None

    @classmethod
    def from_audio_model(cls, audio, metadata: Optional[dict] = None) -> "AudioDetailResponse":
        """Create AudioDetailResponse from Audio model and metadata"""
        metadata_response = AudioMetadataResponse(**metadata) if metadata else None
        
        return cls(
            id=audio.id,
            file_path=audio.file_path,
            processed_file_path=audio.processed_file_path,
            storage_provider=audio.storage_provider.value,
            format=audio.format.value if audio.format else None,
            file_size_bytes=audio.file_size_bytes,
            duration_seconds=audio.duration_seconds,
            sample_rate=audio.sample_rate,
            channels=audio.channels,
            bit_rate=audio.bit_rate,
            recording_started_at=audio.recording_started_at,
            recording_ended_at=audio.recording_ended_at,
            created_at=audio.created_at,
            is_deleted=audio.is_deleted,
            deleted_at=audio.deleted_at,
            meeting_id=audio.meeting_id,
            metadata=metadata_response
        )

    @model_validator(mode="after")
    def format_recording_duration(self) -> "AudioDetailResponse":
        if self.recording_started_at and self.recording_ended_at:
            duration = self.recording_ended_at - self.recording_started_at
            self.recording_duration_formatted = str(duration)
        return self