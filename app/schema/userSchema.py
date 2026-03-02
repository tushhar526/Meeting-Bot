from pydantic import Field, EmailStr, BaseModel
from typing import Optional
from app.helper.validations import PasswordStr


class UserCreate(BaseModel):
    username: str = Field(max_length=100)
    password: PasswordStr
    email: EmailStr


class UserLogin(BaseModel):
    username: str = Field(max_length=100)
    password: PasswordStr


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, max_length=100)
    password: Optional[PasswordStr] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)


class UserResponse(BaseModel):
    user_id: int
    username: str

    class Config:
        from_attributes = True
