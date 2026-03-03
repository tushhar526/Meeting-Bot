from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controller.userController import (
    get_user_profile,
    update_user_profile,
    change_password,
    delete_user_account,
    get_user_analytics,
    get_meeting_trends,
    get_all_bot_details,
    get_bot_detail,
)

user_bp = Blueprint("user_bp", __name__, url_prefix="/users")


@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    return get_user_profile(user_id)


@user_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    return update_user_profile(user_id, request)


@user_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password_route():
    user_id = get_jwt_identity()
    return change_password(user_id, request)


@user_bp.route("/account", methods=["DELETE"])
@jwt_required()
def delete_account():
    user_id = get_jwt_identity()
    return delete_user_account(user_id)


@user_bp.route("/analytics", methods=["GET"])
@jwt_required()
def get_analytics():
    user_id = get_jwt_identity()
    return get_user_analytics(user_id)


@user_bp.route("/analytics/trends", methods=["GET"])
@jwt_required()
def get_trends():
    user_id = get_jwt_identity()
    days = request.args.get('days', 30, type=int)
    return get_meeting_trends(user_id, days)


# Legacy routes for backward compatibility
@user_bp.route("/get_bot_info")
@jwt_required()
def get_bot_info():
    user_id = get_jwt_identity()
    return get_all_bot_details(request)
