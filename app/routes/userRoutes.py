from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controller.userController import (
    get_all_bot_details,
    get_bot_detail,
    update_cred,
)

user_bp = Blueprint("user_bp", __name__, url_prefix="users")


@user_bp.route("/get_bot_info")
@jwt_required()
def get_bot_info():
    user_id = get_jwt_identity()
    return get_all_bot_details(request)
