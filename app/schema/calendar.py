from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CalendarAuthRequest(BaseModel):
    """Request model for calendar authorization"""
    pass


class CalendarAuthResponse(BaseModel):
    """Response model for calendar authorization"""
    access_token: str
    refresh_token: Optional[str]
    expires_in: Optional[int]
    token_type: str
    user_email: str
    user_name: Optional[str]
    message: str


class CalendarTokenRequest(BaseModel):
    """Request model for token-based operations"""
    access_token: str
    refresh_token: str
    days_ahead: Optional[int] = 7


class CalendarEvent(BaseModel):
    """Calendar event model"""
    id: str
    title: str
    description: str
    start_time: str
    end_time: str
    meeting_link: Optional[str]
    platform: str
    all_day: bool
    location: str
    attendees: int


class CalendarEventsResponse(BaseModel):
    """Response model for calendar events"""
    meetings: List[CalendarEvent]
    count: int
    message: str


class CalendarJobCreateRequest(BaseModel):
    """Request model for creating job from calendar event"""
    event_id: str
    access_token: str
    refresh_token: str
    custom_title: Optional[str] = None
    custom_output_path: Optional[str] = None


class CalendarJobResponse(BaseModel):
    """Response model for calendar job creation"""
    job_id: int
    meeting_url: str
    meeting_title: str
    scheduled_time: str
    message: str


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh"""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Response model for token refresh"""
    access_token: str
    expires_in: Optional[int]
    token_type: str
    message: str


class CalendarDisconnectRequest(BaseModel):
    """Request model for calendar disconnection"""
    user_email: str


class CalendarDisconnectResponse(BaseModel):
    """Response model for calendar disconnection"""
    message: str
