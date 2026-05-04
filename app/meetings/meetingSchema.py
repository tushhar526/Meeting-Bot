from pydantic import BaseModel, HttpUrl, model_validator, ConfigDict
from typing import Optional
from datetime import datetime
from app.util.time_util import format_ist_datetime


class CreateBotRequest(BaseModel):
    meeting_url: HttpUrl
    platform: Optional[str] = None
    title: Optional[str] = None

    @model_validator(mode="after")
    def set_default_title(self) -> "CreateBotRequest":
        if not self.title:
            platform_titles = {
                "meet.google.com": "Google Meet Meeting",
                "zoom.us": "Zoom Meeting",
                "teams.microsoft.com": "Microsoft Teams Meeting",
                "teams.live.com": "Microsoft Teams Meeting",
            }
            for domain, label in platform_titles.items():
                if domain in str(self.meeting_url).lower():
                    self.title = label
                    break
            else:
                self.title = "Meeting"
        return self


class BotStatusResponse(BaseModel):
    """Lightweight response for bot status endpoint."""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat() if v else None})

    status: str
    platform: str
    title: str
    created_at: Optional[datetime] = None
    created_at_formatted: Optional[str] = None
    started_at: Optional[datetime] = None
    started_at_formatted: Optional[str] = None

    @model_validator(mode="after")
    def format_dates(self) -> "BotStatusResponse":
        self.created_at_formatted = format_ist_datetime(self.created_at)
        self.started_at_formatted = format_ist_datetime(self.started_at)
        return self


class MeetingResponse(BaseModel):
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat() if v else None})

    id: int
    meeting_url: str
    title: str
    status: str
    platform: str
    created_at: Optional[datetime] = None
    created_at_formatted: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    scheduled_time_formatted: Optional[str] = None
    started_at: Optional[datetime] = None
    started_at_formatted: Optional[str] = None
    ended_at: Optional[datetime] = None
    ended_at_formatted: Optional[str] = None
    bot_join_time: Optional[datetime] = None
    bot_join_time_formatted: Optional[str] = None
    bot_leave_time: Optional[datetime] = None
    bot_leave_time_formatted: Optional[str] = None
    waiting_room_entered_at: Optional[datetime] = None
    waiting_room_entered_at_formatted: Optional[str] = None
    participant_count: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    @model_validator(mode="after")
    def format_dates(self) -> "MeetingResponse":
        self.created_at_formatted = format_ist_datetime(self.created_at)
        self.scheduled_time_formatted = format_ist_datetime(self.scheduled_time)
        self.started_at_formatted = format_ist_datetime(self.started_at)
        self.ended_at_formatted = format_ist_datetime(self.ended_at)
        self.bot_join_time_formatted = format_ist_datetime(self.bot_join_time)
        self.bot_leave_time_formatted = format_ist_datetime(self.bot_leave_time)
        self.waiting_room_entered_at_formatted = format_ist_datetime(self.waiting_room_entered_at)
        return self

