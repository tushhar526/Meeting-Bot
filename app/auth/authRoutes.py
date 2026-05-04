from fastapi import Response, Request
from app.core.database import get_db
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from app.util.response_util.response_cookie_setter import (
    set_auth_cookie,
    clear_auth_cookie,
)
from app.util.response_util.response import SuccessResponse
from .authSchema import RegisterUser, LoginUser, ResetPasswordSchema
from app.core.middlewares.jwt_authenticator import get_current_user_id
from app.email.emailSchema import SendEmailSchema, EmailType
from .authController import (
    signup_controller,
    login_controller,
    refresh_access_token_controller,
    update_password_controller,
    check_token_controller,
)
from app.email.emailController import send_verification_email
from app.core.middlewares.global_logger import get_logger

logger = get_logger("AUTH")

authrouter = APIRouter(prefix="/auth", tags=["Auth"])


@authrouter.post("/signup")
async def auth_signup(
    data: RegisterUser,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):

    verification_token = request.cookies.get("verification_token")

    logger.info(
        f"Signup attempt for user: {data.username}, email: {data.email[:10]}..."
    )

    if not verification_token:
        logger.warning("Signup attempted without verification token")
        from app.util.response_util.custom_exception import MissingVerificationToken

        raise MissingVerificationToken(
            "Email verification required. Please verify your email first."
        )

    result = await signup_controller(
        db=db, data=data, verification_token=verification_token
    )

    # Set auth cookies
    set_auth_cookie(response, result["access_token"], "access")
    set_auth_cookie(response, result["refresh_token"], "refresh")

    # Clean up verification cookie
    clear_auth_cookie(response, "verification")

    logger.info(f"User {data.username} registered successfully")

    return SuccessResponse(message="User successfully registered", data=result["user"])


@authrouter.post("/login")
async def auth_login(
    data: LoginUser, response: Response, db: Session = Depends(get_db)
):
    """
    Login endpoint - sets access and refresh token cookies.
    """
    logger.info(f"Login attempt for user: {data.username}")

    result = login_controller(db, data)

    set_auth_cookie(response, result["access_token"], "access")
    set_auth_cookie(response, result["refresh_token"], "refresh")

    logger.info(f"User {data.username} logged in successfully")

    return SuccessResponse(message="User successfully logged in", data=result["user"])


@authrouter.post("/refreshToken")
async def auth_refresh_token(request: Request, response: Response):
    """
    Refresh access token using refresh token cookie.
    """
    refresh_token = request.cookies.get("refresh_token")

    logger.info("Token refresh attempt")

    result = refresh_access_token_controller(refresh_token)

    set_auth_cookie(response, result["access_token"], "access")

    logger.info("Token refreshed successfully")

    return SuccessResponse(message="Token refreshed")


@authrouter.get("/me")
async def auth_me(
    user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Get current authenticated user info.
    """
    result = check_token_controller(user_id, db)
    return SuccessResponse(message="Valid token", data=result)


@authrouter.post("/forgot-password")
async def auth_forgot_password(data: SendEmailSchema):
    result = send_verification_email(data, email_type=EmailType.FORGOT_PASSWORD)
    return SuccessResponse(message=result["message"])


@authrouter.post("/update-password")
async def auth_update_password(
    data: ResetPasswordSchema,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Update password endpoint - requires verification_token cookie.
    """
    verification_token = request.cookies.get("verification_token")

    logger.info("Password update attempt")

    if not verification_token:
        logger.warning("Password update attempted without verification token")
        from app.util.response_util.custom_exception import MissingVerificationToken

        raise MissingVerificationToken("Email verification required")

    result = await update_password_controller(
        db=db, data=data, verification_token=verification_token
    )

    # Clean up verification cookie
    clear_auth_cookie(response, "verification")

    logger.info("Password updated successfully")

    return SuccessResponse(message="Password updated successfully")
