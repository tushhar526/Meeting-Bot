from .emailService import send_verification_email_service, verify_otp_service
from .emailSchema import SendEmailSchema, VerifyEmailSchema
from .email_enum import EmailType


async def send_verification_email(data: SendEmailSchema, email_type=EmailType.SIGNUP):
    return await send_verification_email_service(data, email_type)


async def verify_otp(data: VerifyEmailSchema):
    return await verify_otp_service(data)
