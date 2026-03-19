from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controller.authController import (
    signup,
    login,
    logout,
    checkToken,
    refreshToken,
)


auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")


@auth_bp.route("/signup", methods=["POST"])
def auth_signup():
    return signup(request)


@auth_bp.route("/login", methods=["POST"])
def auth_login():
    print("The request is like this = ",request)
    return login(request)


@auth_bp.route("/logout", methods=["POST"])
def auth_logout():
    return logout()


@auth_bp.route("/me")
@jwt_required()
def auth_token():
    user_id = get_jwt_identity()
    return checkToken(user_id)


@auth_bp.route("/refreshToken", methods=["POST"])
@jwt_required(refresh=True)
def auth_refresh_token():
    user_id = get_jwt_identity()
    return refreshToken(user_id)
