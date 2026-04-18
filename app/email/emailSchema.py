from pydantic import BaseModel, EmailStr


class SendEmailSchema(BaseModel):
    username: str
    email: EmailStr


class VerifyEmailSchema(BaseModel):
    email: EmailStr
    otp: str

class VerifyOTPResponse(BaseModel):
    message: str
    verification_token: str
