from sqlalchemy.orm import Session
from .authSchema import RegisterUser, LoginUser, ResetPasswordSchema
from app.util.response_util.custom_exception import MissingVerificationToken
from .authService import (
    signup_service,
    login_service,
    refresh_access_token_service,
    check_token_service,
    update_password_service,
)
from app.core.middlewares.global_logger import get_logger

logger = get_logger("AUTH_CONTROLLER")


async def signup_controller(
    db: Session, data: RegisterUser, verification_token: str
) -> dict:
    """
    Controller for user signup.
    Validates verification token and delegates to service layer.
    """
    if not verification_token:
        logger.warning("Signup attempted without verification token in controller")
        raise MissingVerificationToken("Verification token is required")

    return await signup_service(db, data, verification_token)


def login_controller(db: Session, data: LoginUser) -> dict:
    """
    Controller for user login.
    Delegates to service layer for authentication.
    """
    return login_service(db, data)


def refresh_access_token_controller(refresh_token: str) -> dict:
    """
    Controller for refreshing access token.
    """
    return refresh_access_token_service(refresh_token)


def check_token_controller(user_id: int, db: Session) -> dict:
    """
    Controller for validating user token and returning user info.
    """
    return check_token_service(user_id, db)


async def update_password_controller(
    db: Session, data: ResetPasswordSchema, verification_token: str
):
    if not verification_token:
        logger.warning("Password update attempted without verification token in controller")
        raise MissingVerificationToken("Verification token is required")

    return await update_password_service(
        db=db, data=data, verification_token=verification_token
    )
