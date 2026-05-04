from fastapi.concurrency import run_in_threadpool
from app.core.email import send_signup_otp_email, send_forgot_password_email
from app.core.config import setting
from app.util.response_util.custom_exception import (
    AppException,
    AlreadyExistError,
    InvalidOTPError,
    OTPExpiredError,
)
from .emailSchema import SendEmailSchema, VerifyEmailSchema, VerifyOTPResponse
from app.core.redis import redis_client
from app.core.security import generate_OTP, generate_token
from app.core.middlewares.global_logger import get_logger
from app.users.userModel import Users
from sqlalchemy.orm import Session
from .email_enum import EmailType


logger = get_logger("EMAIL")


EMAIL_SENDER_MAP = {
    EmailType.SIGNUP: send_signup_otp_email,
    EmailType.FORGOT_PASSWORD: send_forgot_password_email,
}


async def send_verification_email_service(
    db: Session, data: SendEmailSchema, email_type: str
):
    otp_stored = False

    try:
        existing_user = db.query(Users).filter(Users.email == data.email).first()

        if existing_user:
            logger.warning(f"User with this email already exists {data.email}")
            raise AlreadyExistError("User already exists")

        otp = generate_OTP()

        await redis_client.set(f"otp:{data.email}", otp, ex=setting.REDIS_DATA_EXPIRE)
        otp_stored = True
        logger.info(f"OTP stored in Redis for {data.email}")

        email_func = EMAIL_SENDER_MAP.get(email_type)

        success = await run_in_threadpool(email_func, data.email, data.username, otp)

        if not success:
            if otp_stored:
                await redis_client.delete(f"otp:{data.email}")

            logger.warning(f"Email could not be sent to {data.email}")
            raise AppException("Failed to send email")

        return {"message": "OTP sent successfully"}

    except AppException:
        raise

    except Exception as e:
        if otp_stored:
            await redis_client.delete(f"otp:{data.email}")

        logger.error(f"Unexpected error while sending email to {data.email}: {str(e)}")
        raise AppException("Couldn't send the Email")


async def verify_otp_service(data: VerifyEmailSchema):
    try:
        logger.info(f"OTP verification attempt for email: {data.email[:10]}...")

        stored_otp = await redis_client.get(f"otp:{data.email}")

        if not stored_otp:
            logger.warning(f"OTP not found or expired for email: {data.email[:10]}...")
            raise OTPExpiredError("This OTP is expired")

        if data.otp != stored_otp:
            logger.warning(f"Invalid OTP entered for email: {data.email[:10]}...")
            raise InvalidOTPError("The entered OTP is invalid")

        await redis_client.delete(f"otp:{data.email}")

        verification_token = generate_token("verification", data.email)
        redis_key = f"verify:{verification_token}"

        await redis_client.set(
            redis_key,
            data.email,
            ex=int(setting.VERIFICATION_TOKEN_EXPIRE),
        )

        logger.info(
            f"Verification token generated and stored for email: {data.email[:10]}... "
            f"(expires in {setting.VERIFICATION_TOKEN_EXPIRE}s)"
        )

        return VerifyOTPResponse(
            message="OTP verified successfully", verification_token=verification_token
        )

    except AppException as e:
        raise
