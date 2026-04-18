from sqlalchemy.orm import Session
from app.core import password_hasher, generate_token, decode_token, redis_client
from app.users.userModel import Users
from sqlalchemy.exc import IntegrityError
from .authSchema import RegisterUser, LoginUser, UserCheckResponse, ResetPasswordSchema
from app.core.middlewares.global_logger import get_logger
from .verification_service import validate_verification_token
from app.util import (
    AlreadyExistError,
    AuthenticationError,
    VerificationEmailMismatch,
    AppException,
    UserNotFoundError,
)

logger = get_logger("AUTH")


async def signup_service(db: Session, data: RegisterUser, verification_token: str):
    try:
        logger.info("User signup attempt initiated")

        stored_email = validate_verification_token(
            verification_token=verification_token
        )

        if data.email != stored_email:
            raise VerificationEmailMismatch("Provided Email is not verified")

        await redis_client.delete(f"verify:{verification_token}")

        existing_user = db.query(Users).filter(Users.email == data.email).first()

        if existing_user:
            logger.warning(f"User with this email already exists {data.email}")
            raise AlreadyExistError("User already exists")

        existing_user = db.query(Users).filter(Users.username == data.username).first()
        if existing_user:
            logger.warning(f"User with this username already exists {data.username}")
            raise AlreadyExistError("User already exists")

        hashed_password = password_hasher(data.password)

        user = Users(
            email=data.email,
            username=data.username,
            password=hashed_password,
            organization_name=data.organization_name,
        )

        db.add(user)

        logger.info("User added to the Db successfully")

        db.commit()
        db.refresh(user)

        access_token = generate_token("access", user.id)
        refresh_token = generate_token("refresh", user.id)

        result = {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

        return result

    except IntegrityError:
        db.rollback()
        raise AlreadyExistError("User already exists")

    except AppException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {str(e)}")
        raise AppException("Something went wrong")


def login_service(db: Session, data: LoginUser):
    try:
        logger.info("User login attempt initiated")

        user = db.query(Users).filter_by(username=data.username).first()

        if not user:
            logger.warning(f"No such User Found with username = {data.username}")
            raise UserNotFoundError("No such User Found")

        if not password_hasher.verify(data.password, user.password):
            logger.warning(f"Password Didn't matched for the user {user.username}")
            raise AuthenticationError("Entered Credentials are invalid")

        access_token = generate_token("access", user.id)
        refresh_token = generate_token("refresh", user.id)

        result = {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

        return result

    except AuthenticationError:
        raise

    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise AppException("Something went wrong")


def refresh_access_token_service(refresh_token: str):

    logger.info("Refresh Access Token Service entered")

    if not refresh_token:
        raise AuthenticationError("Not logged in")

    user_id = decode_token(refresh_token)

    new_access_token = generate_token("access", user_id)

    return {"access_token": new_access_token}


def check_token_service(user_id: int, db: Session):
    logger.info(f"Token validation check for user_id: {user_id}")

    user = db.query(Users).filter(Users.id == user_id).first()

    if not user:
        logger.warning("Token validation failed - invalid user_id", user_id=user_id)
        raise AuthenticationError("Invalid token")

    user_response = UserCheckResponse.model_validate(user)

    logger.info("Token validated successfully", user_id=user_id)

    return {"data": user_response}


async def update_password_service(
    db: Session, verification_token: str, data: ResetPasswordSchema
):
    try:
        logger.info("Update Password Service entered")

        stored_email = await validate_verification_token(verification_token)

        user = db.query(Users).filter_by(email=stored_email).first()

        if not user:
            raise UserNotFoundError()

        user.password = password_hasher(data.new_password)

        db.commit()

        await redis_client.delete(f"verify:{verification_token}")

    except AppException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Update password error: {str(e)}")
        raise AppException("Something went wrong")
