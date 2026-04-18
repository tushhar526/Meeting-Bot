from fastapi.concurrency import run_in_threadpool
from app.core import send_signup_otp_email, setting, send_forgot_password_email
from app.util import AppException, InvalidOTPError, OTPExpiredError
from .emailSchema import SendEmailSchema, VerifyEmailSchema, VerifyOTPResponse
from app.core import redis_client, generate_OTP, get_logger, generate_token
from .email_enum import EmailType


logger = get_logger("EMAIL")


EMAIL_SENDER_MAP = {
    EmailType.SIGNUP: send_signup_otp_email,
    EmailType.FORGOT_PASSWORD: send_forgot_password_email,
}


async def send_verification_email_service(data: SendEmailSchema, email_type: str):
    otp_stored = False

    try:
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
        stored_otp_bytes = await redis_client.get(f"otp:{data.email}")

        if not stored_otp_bytes:
            raise OTPExpiredError("This Otp is Expired")

        stored_otp = stored_otp_bytes.decode()

        if data.otp != stored_otp:
            raise InvalidOTPError("The Entered Otp is Invalid")

        await redis_client.delete(f"otp:{data.email}")

        verification_token = generate_token("verification", data.email)

        await redis_client.set(
            f"verify:{verification_token}",
            data.email,
            ex=setting.VERIFICATION_TOKEN_EXPIRE,
        )

        return VerifyOTPResponse(
            message="OTP verified successfully", verification_token=verification_token
        )

    except AppException as e:
        raise
