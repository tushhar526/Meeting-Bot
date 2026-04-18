from fastapi import APIRouter, Response
from .emailSchema import SendEmailSchema, VerifyEmailSchema
from .emailController import send_verification_email, verify_otp
from app.util import SuccessResponse, set_auth_cookie

router = APIRouter()


@router.post("/send-verification-email")
async def send_email_route(data: SendEmailSchema):
    result = await send_verification_email(data)
    return SuccessResponse(message=result["message"])


@router.post("/verify-otp")
async def verify_otp_route(data: VerifyEmailSchema, respones: Response):
    result = await verify_otp(data.email, data.otp)

    set_auth_cookie(
        respones, token=result.verification_token, token_type="verification"
    )

    return SuccessResponse(message=result.message)
