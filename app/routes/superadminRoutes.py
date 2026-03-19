from flask import Blueprint, request, jsonify
from app.controller.superAdminController.planController import (
    create_plan, update_plan, delete_plan, get_all_plans, get_plan, get_active_plans
)
from app.controller.superAdminController.userManagementController import (
    get_all_users, get_user_details, deactivate_user_plan, assign_plan_to_user,
    soft_delete_user, restore_user, get_deleted_users, update_user_role, toggle_user_status
)
from app.controller.superAdminController.logManagementController import (
    get_all_logs_handler, get_log_stats_handler, get_security_logs_handler,
    export_logs_handler, clear_old_logs_handler
)
from app.controller.superAdminController.subscriptionManagementController import (
    get_all_users_subscriptions, assign_subscription, cancel_user_subscription,
    get_my_subscription, get_subscription_stats, bulk_subscription_update,
    get_expiring_subscriptions, extend_subscription
)
from flask_jwt_extended import jwt_required
from app.helper.decorators import require_super_admin, require_auth

superadmin_bp = Blueprint("superadmin_bp", __name__, url_prefix="/superadmin")


# Plan Management Routes
@superadmin_bp.route("/plans", methods=["POST"])
@jwt_required()
@require_super_admin
def create_plan_route():
    """Create a new plan"""
    return create_plan(request)


@superadmin_bp.route("/plans", methods=["GET"])
@jwt_required()
@require_super_admin
def get_all_plans_route():
    """Get all plans"""
    return get_all_plans()


@superadmin_bp.route("/plans/<int:plan_id>", methods=["GET"])
@jwt_required()
@require_super_admin
def get_plan_route(plan_id):
    """Get a specific plan"""
    return get_plan(plan_id)


@superadmin_bp.route("/plans/<int:plan_id>", methods=["PUT"])
@jwt_required()
@require_super_admin
def update_plan_route(plan_id):
    """Update a plan"""
    return update_plan(plan_id, request)


@superadmin_bp.route("/plans/<int:plan_id>", methods=["DELETE"])
@jwt_required()
@require_super_admin
def delete_plan_route(plan_id):
    """Delete/deactivate a plan"""
    return delete_plan(plan_id)


# User Management Routes
@superadmin_bp.route("/users", methods=["GET"])
@jwt_required()
@require_super_admin
def get_all_users_route():
    """Get all users with their plan information"""
    return get_all_users()


@superadmin_bp.route("/users/<int:user_id>", methods=["GET"])
@jwt_required()
@require_super_admin
def get_user_details_route(user_id):
    """Get detailed information about a specific user"""
    return get_user_details(user_id)


@superadmin_bp.route("/users/<int:user_id>/plan/deactivate", methods=["POST"])
@jwt_required()
@require_super_admin
def deactivate_user_plan_route(user_id):
    """Deactivate a user's plan"""
    return deactivate_user_plan(user_id)


@superadmin_bp.route("/users/<int:user_id>/plan/assign", methods=["POST"])
@jwt_required()
@require_super_admin
def assign_plan_to_user_route(user_id):
    """Assign a plan to a user"""
    return assign_plan_to_user(user_id, request)


# Additional User Management Routes
@superadmin_bp.route("/users/<int:user_id>/soft-delete", methods=["POST"])
@jwt_required()
@require_super_admin
def soft_delete_user_route(user_id):
    """Soft delete a user"""
    return soft_delete_user(user_id)


@superadmin_bp.route("/users/<int:user_id>/restore", methods=["POST"])
@jwt_required()
@require_super_admin
def restore_user_route(user_id):
    """Restore a soft deleted user"""
    return restore_user(user_id)


@superadmin_bp.route("/users/deleted", methods=["GET"])
@jwt_required()
@require_super_admin
def get_deleted_users_route():
    """Get all soft deleted users"""
    return get_deleted_users()


@superadmin_bp.route("/users/<int:user_id>/role", methods=["PUT"])
@jwt_required()
@require_super_admin
def update_user_role_route(user_id):
    """Update a user's role"""
    return update_user_role(user_id)


@superadmin_bp.route("/users/<int:user_id>/toggle-status", methods=["POST"])
@jwt_required()
@require_super_admin
def toggle_user_status_route(user_id):
    """Activate or deactivate a user account"""
    return toggle_user_status(user_id)


# Log Management Routes
@superadmin_bp.route("/logs", methods=["GET"])
@jwt_required()
@require_super_admin
def get_all_logs_route():
    """Get all system logs"""
    return get_all_logs_handler()


@superadmin_bp.route("/logs/stats", methods=["GET"])
@jwt_required()
@require_super_admin
def get_log_stats_route():
    """Get log statistics"""
    return get_log_stats_handler()


@superadmin_bp.route("/logs/security", methods=["GET"])
@jwt_required()
@require_super_admin
def get_security_logs_route():
    """Get security-related logs"""
    return get_security_logs_handler()


@superadmin_bp.route("/logs/export", methods=["GET"])
@jwt_required()
@require_super_admin
def export_logs_route():
    """Export logs to CSV"""
    return export_logs_handler()


@superadmin_bp.route("/logs/clear", methods=["POST"])
@jwt_required()
@require_super_admin
def clear_old_logs_route():
    """Clear old logs"""
    return clear_old_logs_handler()


# Subscription Management Routes
@superadmin_bp.route("/subscriptions/users", methods=["GET"])
@jwt_required()
@require_super_admin
def get_all_users_subscriptions_route():
    """Get all users with their subscription details"""
    return get_all_users_subscriptions()


@superadmin_bp.route("/subscriptions/users/<int:user_id>/assign", methods=["POST"])
@jwt_required()
@require_super_admin
def assign_subscription_route(user_id):
    """Assign or update subscription for a user"""
    return assign_subscription(user_id)


@superadmin_bp.route("/subscriptions/users/<int:user_id>/cancel", methods=["POST"])
@jwt_required()
@require_super_admin
def cancel_user_subscription_route(user_id):
    """Cancel user subscription"""
    return cancel_user_subscription(user_id)


@superadmin_bp.route("/subscriptions/stats", methods=["GET"])
@jwt_required()
@require_super_admin
def get_subscription_stats_route():
    """Get subscription statistics"""
    return get_subscription_stats()


@superadmin_bp.route("/subscriptions/bulk-update", methods=["POST"])
@jwt_required()
@require_super_admin
def bulk_subscription_update_route():
    """Update multiple subscriptions at once"""
    return bulk_subscription_update()


@superadmin_bp.route("/subscriptions/expiring", methods=["GET"])
@jwt_required()
@require_super_admin
def get_expiring_subscriptions_route():
    """Get subscriptions expiring soon"""
    return get_expiring_subscriptions()


@superadmin_bp.route("/subscriptions/users/<int:user_id>/extend", methods=["POST"])
@jwt_required()
@require_super_admin
def extend_subscription_route(user_id):
    """Extend a user's subscription"""
    return extend_subscription(user_id)


# Public Plan Routes (no auth required)
@superadmin_bp.route("/plans/public", methods=["GET"])
def get_active_plans_route():
    """Get all active plans for public access"""
    return get_active_plans()


# User Subscription Routes (for authenticated users)
@superadmin_bp.route("/subscriptions/my", methods=["GET"])
@jwt_required()
@require_auth
def get_my_subscription_route():
    """Get current user's subscription details"""
    from flask_jwt_extended import get_jwt_identity
    from app.models.userModel import userModel
    
    user_id = get_jwt_identity()
    user = userModel.query.filter_by(user_id=user_id).first()
    return get_my_subscription(user)
