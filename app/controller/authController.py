from app.models.usermodel import UserModel
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


def signup(request):

    try:
        user_data = UserCreate(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    existing_user = UserModel.query.filter_by(username=user_data.username).first()

    if existing_user:
        return jsonify({"message": "User already exists"}), 400

    new_user = UserModel(username=user_data.username, email=user_data.email)

    new_user.set_password(raw_password=user_data.password)

    db.session.add(new_user)
    db.session.commit()

    access_token = create_access_token(identity=new_user.user_id)
    refresh_token = create_refresh_token(identity=new_user.user_id)
    user_response = UserResponse.model_validate(new_user)

    response = jsonify(
        {"message": "Signup SuccessFull", "user": user_response.model_dump()}
    )

    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)

    return response, 201


def login(request):

    try:
        user_data = UserLogin(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    user = UserModel.query.filter_by(username=user_data.username).first()

    if not user or not user.check_password(user_data.password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.user_id)
    refresh_token = create_refresh_token(identity=user.user_id)
    user_response = UserResponse.model_validate(user)

    response = jsonify(
        {
            "message": "Login Successfull",
            "user": user_response.model_dump(),
        }
    )

    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)

    return response, 200


def logout():
    response = jsonify({"message": "Successfully Logout"})

    response.set_cookie(
        "access_token", "", path="/", httponly=True, max_age=0, samesite="Lax"
    )

    response.set_cookie(
        "refresh_token", "", path="/", httponly=True, max_age=0, samesite="Lax"
    )

    return response


def checkToken(user_id):
    user = UserModel.query.filter(user_id=user_id).first()

    if not user:
        return jsonify({"message": "Invalid Token"}), 401

    user_response = UserResponse(user)

    response = jsonify({"meesage": "Valid Token", "user": user_response})

    return response, 200


def refreshToken(user_id):
    user = UserModel.query.filter(user_id).first()

    if not user:
        return jsonify({"message": "Invalid Credentials"}), 401

    access_token = create_access_token(identity=user_id)
    refresh_token = create_refresh_token(identity=user_id)

    response = jsonify({"message": "Token Verified"})
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)

    return response, 200
