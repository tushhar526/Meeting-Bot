from pydantic import Field, BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.planModel import PlanType


class PlanCreate(BaseModel):
    name: str = Field(max_length=100)
    plan_type: PlanType
    description: Optional[str] = None
    price: float = Field(ge=0.0)
    max_meetings: Optional[int] = None
    max_users: Optional[int] = None
    features: Optional[List[str]] = None
    is_active: bool = True


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    plan_type: Optional[PlanType] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    max_meetings: Optional[int] = None
    max_users: Optional[int] = None
    features: Optional[List[str]] = None
    is_active: Optional[bool] = None


class PlanResponse(BaseModel):
    plan_id: int
    name: str
    plan_type: str
    description: Optional[str] = None
    price: float
    max_meetings: Optional[int] = None
    max_users: Optional[int] = None
    features: Optional[str] = None  # JSON string
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def features_list(self) -> List[str]:
        """Convert JSON string to list"""
        if self.features:
            try:
                import json
                return json.loads(self.features)
            except:
                return []
        return []


class PlanWithUsers(PlanResponse):
    users_count: int = 0
