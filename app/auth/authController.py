from sqlalchemy.orm import Session
from .authSchema import RegisterUser, LoginUser, ResetPasswordSchema
from app.util import MissingVerificationToken
from .authService import (
    signup_service,
    login_service,
    refresh_access_token_service,
    check_token_service,
    update_password_service,
)


async def signup(db: Session, data: RegisterUser, verification_token: str):

    if not verification_token:
        raise MissingVerificationToken("Verification Token Is required")

    return await signup_service(db, data, verification_token)


def login(db: Session, data: LoginUser):
    return login_service(db, data)


def refreh_access_token(refresh_token: str):
    return refresh_access_token_service(refresh_token)


def check_token(user_id: int, db: Session):
    return check_token_service(user_id, db)


async def update_password(
    db: Session, data: ResetPasswordSchema, verification_token: str
):
    if not verification_token:
        raise MissingVerificationToken("Verification Token Is required")

    return await update_password_service(
        db=db, data=data, verification_token=verification_token
    )
