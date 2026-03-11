from pydantic import Field, EmailStr, BaseModel
from typing import Optional, Dict, Any
from app.helper.validations import PasswordStr
from datetime import datetime
from app.models.userModel import UserRole, SubscriptionStatus


class UserCreate(BaseModel):
    username: str = Field(max_length=100)
    password: PasswordStr
    email: EmailStr
    organization_name: Optional[str] = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    username: str = Field(max_length=100)
    password: PasswordStr


class UserResponse(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    organization_name: Optional[str] = None
    role: UserRole
    plan_id: Optional[int] = None
    subscription_status: SubscriptionStatus
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    is_active: bool
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    meetings: int
    plan: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, max_length=100)
    password: Optional[PasswordStr] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    organization_name: Optional[str] = Field(default=None, max_length=255)
    role: Optional[UserRole] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class UserSubscriptionUpdate(BaseModel):
    plan_id: Optional[int] = Field(default=None)
    subscription_status: Optional[SubscriptionStatus] = Field(default=None)
    subscription_end_date: Optional[datetime] = Field(default=None)
