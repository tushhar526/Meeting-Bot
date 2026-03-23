from pydantic import Field, EmailStr, BaseModel, ConfigDict
from typing import Optional, Dict, Any
from app.helper.validations import PasswordStr
from datetime import datetime
from app.models.userModel import UserRole, SubscriptionStatus


class UserCreate(BaseModel):
    username: str = Field(max_length=100)
    password: PasswordStr
    email: EmailStr
    organization_name: str = Field(max_length=255)


class UserLogin(BaseModel):
    username: str = Field(max_length=100)
    password: PasswordStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    username: str
    email: EmailStr
    organization_name: Optional[str] = None
    role: UserRole
    plan_id: Optional[int] = None
    is_active: bool
    meetings: int
    plan: Optional[Dict[str, Any]] = None

    @classmethod
    def model_validate(cls, obj):
        """Custom validation to handle plan relationship"""
        if hasattr(obj, 'plan') and obj.plan:
            # Convert PlanModel to dictionary
            plan_dict = {
                "plan_id": obj.plan.plan_id,
                "name": obj.plan.name,
                "plan_type": obj.plan.plan_type,
                "description": obj.plan.description,
                "price": float(obj.plan.price),
                "max_meetings": obj.plan.max_meetings,
                "max_users": obj.plan.max_users,
                "is_active": obj.plan.is_active,
            }
            # Create a copy of the object with plan as dict
            class UserWithPlanDict:
                def __init__(self, user_obj, plan_dict):
                    for attr in dir(user_obj):
                        if not attr.startswith('_'):
                            setattr(self, attr, getattr(user_obj, attr))
                    self.plan = plan_dict
            
            obj_with_plan_dict = UserWithPlanDict(obj, plan_dict)
            return super().model_validate(obj_with_plan_dict)
        
        return super().model_validate(obj)


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
