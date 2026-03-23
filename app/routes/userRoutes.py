from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.controller import (
    get_user_profile,
    update_user_profile,
    change_password,
    get_user_analytics,
    get_meeting_trends,
    get_all_plans,
    assign_plan_to_user,
    get_user_plan_status,
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
    days = request.args.get("days", 30, type=int)
    return get_meeting_trends(user_id, days)


@user_bp.route("/plans", methods=["GET"])
@jwt_required()
def get_plans_route():
    user_id = get_jwt_identity()
    return get_all_plans(user_id)


@user_bp.route("/plans/assign", methods=["POST"])
@jwt_required()
def assign_plan_route():
    user_id = get_jwt_identity()
    data = request.json or {}
    plan_type = data.get("plan_type")
    return assign_plan_to_user(user_id, plan_type)


@user_bp.route("/plans/status", methods=["GET"])
@jwt_required()
def plan_status_route():
    user_id = get_jwt_identity()
    return get_user_plan_status(user_id)


# Legacy routes for backward compatibility
# @user_bp.route("/get_bot_info")
# @jwt_required()
# def get_bot_info():
#     user_id = get_jwt_identity()
#     return get_all_bot_details(request)
