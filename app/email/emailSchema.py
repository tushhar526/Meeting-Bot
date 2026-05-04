from enum import Enum
from pydantic import BaseModel, EmailStr


class EmailType(str, Enum):
    VERIFICATION = "verification"
    FORGOT_PASSWORD = "forgot_password"


class SendEmailSchema(BaseModel):
    username: str
    email: EmailStr


class VerifyEmailSchema(BaseModel):
    email: EmailStr
    otp: str

class VerifyOTPResponse(BaseModel):
    message: str
    verification_token: str
