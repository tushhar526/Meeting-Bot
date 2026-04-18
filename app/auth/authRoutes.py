from fastapi import Response, Request
from app.core import get_db
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from app.util import set_auth_cookie
from app.util import SuccessResponse
from .authSchema import RegisterUser, LoginUser, ResetPasswordSchema
from app.core.middlewares.jwt_authenticator import get_current_user_id
from app.email import SendEmailSchema, EmailType
from .authController import (
    signup,
    login,
    refreh_access_token,
    update_password,
    check_token,
)
from app.email import send_verification_email

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup")
async def auth_signup(
    data: RegisterUser,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):

    verification_token = request.cookies.get("verification_token")

    result = await signup(db=db, data=data, verification_token=verification_token)

    set_auth_cookie(response, result["access_token"], "access")
    set_auth_cookie(response, result["refresh_token"], "refresh")

    response.delete_cookie("verification_token")

    return SuccessResponse(message="User SuccessFully Registered", data=result["user"])


@router.post("./login")
def auth_login(data: LoginUser, response: Response, db: Session = Depends(get_db)):
    result = login(db, data)

    set_auth_cookie(response, result["access_token"], "access")
    set_auth_cookie(response, result["refresh_token"], "refresh")

    return SuccessResponse(message="User SuccessFully Logged IN", data=result["user"])


@router.post("/refresh-token")
def auth_refresh_token(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")

    result = refreh_access_token(refresh_token)

    set_auth_cookie(response, result["access_token"], "access")

    return SuccessResponse(message="Token refreshed")


@router.get("/me")
def auth_token(
    user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    result = check_token(user_id, db)
    return SuccessResponse(message="Valid Token", data=result)


@router.post("/forgot-password")
async def auth_forgot_password(data: SendEmailSchema):
    result = send_verification_email(data, email_type=EmailType.FORGOT_PASSWORD)
    return SuccessResponse(message=result["message"])


@router.post("/update-password")
async def auth_update_password(
    data: ResetPasswordSchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    verification_token = request.cookies.get("verification_token")

    result = await update_password()
    pass
