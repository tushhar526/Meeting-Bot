from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class RecentMeetingData(BaseModel):
    """Data for a single recent meeting"""

    meeting_id: int
    meeting_url: str
    platform: str
    status: str
    created_at: Optional[datetime] = None
    title: str
    participant_count: int
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_hours: Optional[float] = None


class AnalyticsPeriod(BaseModel):
    """Time period information for analytics"""

    week_start: datetime
    month_start: datetime
    current_date: datetime


class UserAnalyticsResponse(BaseModel):
    """Complete user analytics response"""

    total_meetings: int
    completed_meetings: int
    average_duration_hours: float
    this_week_meetings: int
    this_month_meetings: int
    meetings_by_day: Dict[str, int]
    platform_distribution: Dict[str, int]
    recent_meetings: List[RecentMeetingData]
    analytics_period: AnalyticsPeriod
    cached: Optional[bool] = None
    cached_at: Optional[datetime] = None


class UserStatsSummary(BaseModel):
    """Lightweight stats for quick overview"""

    total_meetings: int
    completed_meetings: int
    this_week_meetings: int
    this_month_meetings: int
    average_duration_hours: float


class MeetingTrendsResponse(BaseModel):
    """Meeting trends over a period of days"""

    period_days: int
    start_date: str
    end_date: str
    daily_trends: Dict[str, int]
    total_meetings_in_period: int
    average_per_day: float
