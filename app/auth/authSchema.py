from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from app.users.userModel import UserRole
from app.util import PasswordStr


class RegisterUser(BaseModel):
    username: str = Field(max_length=100)
    password: PasswordStr
    email: EmailStr
    organization_name: str = Field(max_length=255)


class LoginUser(BaseModel):
    username: str = Field(max_length=100)
    password: PasswordStr


class UserCheckResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    organization_name: Optional[str] = None
    role: UserRole
    is_active: bool


class ResetPasswordSchema(BaseModel):
    new_password: PasswordStr
    confirm_password: PasswordStr
