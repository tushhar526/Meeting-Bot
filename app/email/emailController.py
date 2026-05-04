from .emailService import send_verification_email_service, verify_otp_service
from .emailSchema import SendEmailSchema, VerifyEmailSchema
from .email_enum import EmailType
from sqlalchemy.orm import Session


async def send_verification_email(
    db: Session, data: SendEmailSchema, email_type=EmailType.SIGNUP
):
    return await send_verification_email_service(db, data, email_type)


async def verify_otp(data: VerifyEmailSchema):
    return await verify_otp_service(data)
