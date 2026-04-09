from pydantic import BaseModel
from typing import Optional, List


class DiscussionItem(BaseModel):
    problem: Optional[str] = None
    solution: Optional[str] = None
    decision: Optional[str] = None


class MeetingSummary(BaseModel):
    discussions: List[DiscussionItem]
    overview: Optional[str] = None
    conclusion: str
