from fastapi import APIRouter, Response, Depends
from .emailSchema import SendEmailSchema, VerifyEmailSchema
from .emailController import send_verification_email, verify_otp
from app.util.response_util.response import SuccessResponse
from app.util.response_util.response_cookie_setter import set_auth_cookie
from app.core.database import get_db
from sqlalchemy.orm import Session

emailrouter = APIRouter(prefix="/email", tags=["Email"])


@emailrouter.post("/send-verification-email")
async def send_email_route(data: SendEmailSchema, db: Session = Depends(get_db)):
    result = await send_verification_email(db, data)
    return SuccessResponse(message=result["message"])


@emailrouter.post("/verify-otp")
async def verify_otp_route(data: VerifyEmailSchema, response: Response):
    result = await verify_otp(data)

    set_auth_cookie(
        response, token=result.verification_token, token_type="verification"
    )

    return SuccessResponse(message=result.message)
