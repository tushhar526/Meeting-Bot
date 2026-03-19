from app.models.userModel import userModel, UserRole, SubscriptionStatus
from app.models.planModel import PlanModel
from flask import jsonify
from app.extension import jwt
from app.extension import db
from app.schema.userSchema import UserCreate, UserLogin, UserResponse
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
)
from pydantic import ValidationError
from datetime import datetime, timedelta
from app.helper.logger import get_logger

logger = get_logger(__name__)


def signup(request):
    try:
        logger.info("User signup attempt initiated")

        try:
            user_data = UserCreate(**request.json)
            logger.info(f"Signup data validated for username: {user_data.username}")
        except ValidationError as e:
            logger.warning(f"Signup validation failed: {e.errors()}")
            return jsonify({"error": e.errors()}), 400

        existing_user = userModel.query.filter_by(username=user_data.username).first()
        existing_email = userModel.query.filter_by(email=user_data.email).first()

        if existing_user:
            logger.warning(
                f"Signup attempt with existing username: {user_data.username}"
            )
            return jsonify({"message": "Username already exists"}), 400

        if existing_email:
            logger.warning(f"Signup attempt with existing email: {user_data.email}")
            return jsonify({"message": "Email already exists"}), 400

        # Create new user with admin role by default
        if not user_data.organization_name:
            logger.warning("Signup attempt without organization name")
            return jsonify({"message": "Organization name is required"}), 400

        new_user = userModel(
            username=user_data.username,
            email=user_data.email,
            organization_name=user_data.organization_name,
            role=UserRole.ADMIN,
            subscription_status=SubscriptionStatus.INACTIVE,
        )

        new_user.set_password(raw_password=user_data.password)

        db.session.add(new_user)
        db.session.commit()

        logger.auth(
            f"New user created successfully",
            user_id=new_user.user_id,
            details=f"username: {new_user.username}, email: {new_user.email}",
        )

        access_token = create_access_token(identity=new_user.user_id)
        refresh_token = create_refresh_token(identity=new_user.user_id)
        user_response = UserResponse.model_validate(new_user)

        response = jsonify(
            {
                "message": "Signup SuccessFull",
                "user": user_response.model_dump(),
                "note": "User created with admin role.",
            }
        )

        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        return response, 201
    except Exception as e:
        logger.error(
            "Error during user signup",
            exception=e,
            details=f"Request data: {request.json if request else 'No request data'}",
        )
        return jsonify({"message": "Error occured"}), 500


def login(request):
    try:
        logger.info("User login attempt initiated")

        try:
            user_data = UserLogin(**request.json)
            logger.info(f"Login data validated for username: {user_data.username}")
        except ValidationError as e:
            logger.warning(f"Login validation failed: {e.errors()}")
            return jsonify({"error": e.errors()}), 400

        user = userModel.get_by_email_or_username(user_data.username)

        if not user or not user.check_password(user_data.password):
            logger.security(
                f"Login failed - invalid credentials",
                user_id=user.user_id if user else None,
                details=f"username: {user_data.username}",
            )
            return jsonify({"message": "Invalid credentials"}), 401

        access_token = create_access_token(identity=str(user.user_id))
        refresh_token = create_refresh_token(identity=str(user.user_id))
        user_response = UserResponse.model_validate(user)

        response = jsonify(
            {
                "message": "Login Successfull",
                "user": user_response.model_dump(),
            }
        )

        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        logger.auth(
            f"User logged in successfully",
            user_id=user.user_id,
            details=f"username: {user.username}",
        )

        return response, 200
    except Exception as e:
        print("Error in login goes something like this = ", str(e))
        logger.error(
            "Error during user login",
            exception=e,
            details=f"Request data: {request.json if request else 'No request data'}",
        )
        return jsonify({"message": "Internal server error"}), 500


def logout():
    logger.info("User logout attempt")

    response = jsonify({"message": "Successfully Logout"})

    response.set_cookie(
        "access_token", "", path="/", httponly=True, max_age=0, samesite="Lax"
    )

    response.set_cookie(
        "refresh_token", "", path="/", httponly=True, max_age=0, samesite="Lax"
    )

    logger.auth("User logged out successfully")

    return response


def checkToken(user_id):
    logger.info(f"Token validation check for user_id: {user_id}")

    user = userModel.get_active_users().filter(userModel.user_id == user_id).first()

    if not user:
        logger.security(f"Token validation failed - invalid user_id", user_id=user_id)
        return jsonify({"message": "Invalid Token"}), 401

    user_response = UserResponse.model_validate(user)

    logger.auth(f"Token validated successfully", user_id=user_id)

    response = jsonify({"meesage": "Valid Token", "user": user_response.model_dump()})

    return response, 200


def refreshToken(user_id):
    logger.info(f"Token refresh attempt for user_id: {user_id}")

    user = userModel.get_active_users().filter(userModel.user_id == user_id).first()

    if not user:
        logger.security(f"Token refresh failed - invalid user_id", user_id=user_id)
        return jsonify({"message": "Invalid Credentials"}), 401

    access_token = create_access_token(identity=str(user.user_id))
    refresh_token = create_refresh_token(identity=str(user.user_id))

    response = jsonify({"message": "Token Verified"})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)

    logger.auth(f"Token refreshed successfully", user_id=user_id)

    return response, 200
