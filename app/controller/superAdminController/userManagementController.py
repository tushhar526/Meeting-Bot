from flask import jsonify, request
from app.extension import db
from app.models.userModel import userModel, UserRole, SubscriptionStatus
from app.models.planModel import PlanModel
from app.schema.userSchema import UserResponse
from datetime import datetime, timezone
from pydantic import ValidationError
from typing import Optional


def get_all_users():
    """Get all users with their plan information"""
    try:
        users = userModel.get_active_users().all()
        users_data = []
        
        for user in users:
            user_data = {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "organization_name": user.organization_name,
                "role": user.role,
                "is_active": user.is_active,
                "meetings": user.meetings,
                "subscription_status": user.subscription_status,
                "subscription_start_date": user.subscription_start_date.isoformat() if user.subscription_start_date else None,
                "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
                "plan": user.plan.to_dict() if user.plan else None
            }
            users_data.append(user_data)
        
        return jsonify({
            "users": users_data,
            "total": len(users_data)
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get users: {str(e)}"}), 500


def get_user_details(user_id):
    """Get detailed information about a specific user"""
    try:
        user = userModel.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user_data = {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "organization_name": user.organization_name,
            "role": user.role,
            "is_active": user.is_active,
            "meetings": user.meetings,
            "subscription_status": user.subscription_status,
            "subscription_start_date": user.subscription_start_date.isoformat() if user.subscription_start_date else None,
            "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "plan": user.plan.to_dict() if user.plan else None
        }
        
        return jsonify({"user": user_data}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get user details: {str(e)}"}), 500


def deactivate_user_plan(user_id):
    """Deactivate a user's plan"""
    try:
        user = userModel.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if not user.plan_id:
            return jsonify({"error": "User has no active plan"}), 400
        
        # Deactivate user's subscription
        user.subscription_status = SubscriptionStatus.INACTIVE
        user.plan_id = None
        user.subscription_end_date = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            "message": "User plan deactivated successfully",
            "user_id": user_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to deactivate user plan: {str(e)}"}), 500


def assign_plan_to_user(user_id):
    """Assign a plan to a user"""
    try:
        user = userModel.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.json
        plan_id = data.get('plan_id')
        
        if not plan_id:
            return jsonify({"error": "plan_id is required"}), 400
        
        plan = PlanModel.query.get(plan_id)
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
        
        if not plan.is_active:
            return jsonify({"error": "Plan is not active"}), 400
        
        # Assign plan to user
        user.plan_id = plan_id
        user.subscription_status = SubscriptionStatus.ACTIVE
        user.subscription_start_date = datetime.now(timezone.utc)
        
        # Set end date if provided
        if 'subscription_end_date' in data:
            user.subscription_end_date = datetime.fromisoformat(data['subscription_end_date'])
        else:
            # Default to 1 year from now
            user.subscription_end_date = datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1)
        
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            "message": "Plan assigned successfully",
            "user_id": user_id,
            "plan": plan.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to assign plan: {str(e)}"}), 500


def soft_delete_user(user_id):
    """Soft delete a user"""
    try:
        target_user = userModel.get_active_users().filter_by(user_id=user_id).first()
        if not target_user:
            return jsonify({"message": "User not found"}), 404

        target_user.soft_delete()
        db.session.commit()

        return jsonify({
            "message": "User soft deleted successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error deleting user"}), 500


def restore_user(user_id):
    """Restore a soft deleted user"""
    try:
        target_user = userModel.query.filter_by(user_id=user_id, is_deleted=True).first()
        if not target_user:
            return jsonify({"message": "Deleted user not found"}), 404

        target_user.restore()
        db.session.commit()

        user_response = UserResponse.model_validate(target_user)
        if target_user.plan:
            user_response.plan = target_user.plan.to_dict()

        return jsonify({
            "message": "User restored successfully",
            "user": user_response.model_dump()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error restoring user"}), 500


def get_deleted_users():
    """Get all soft deleted users"""
    try:
        deleted_users = userModel.query.filter_by(is_deleted=True).all()
        users_data = []
        
        for user_obj in deleted_users:
            user_dict = UserResponse.model_validate(user_obj).model_dump()
            if user_obj.plan:
                user_dict['plan'] = user_obj.plan.to_dict()
            users_data.append(user_dict)
        
        return jsonify({
            "deleted_users": users_data
        }), 200
    except Exception as e:
        return jsonify({"message": "Error fetching deleted users"}), 500


def update_user_role(user_id):
    """Update a user's role"""
    try:
        user = userModel.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.json
        new_role = data.get('role')
        
        if not new_role:
            return jsonify({"error": "role is required"}), 400
        
        if new_role not in [role.value for role in UserRole]:
            return jsonify({"error": "Invalid role"}), 400
        
        user.role = new_role
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            "message": "User role updated successfully",
            "user_id": user_id,
            "new_role": new_role
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update user role: {str(e)}"}), 500


def toggle_user_status(user_id):
    """Activate or deactivate a user account"""
    try:
        user = userModel.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user.is_active = not user.is_active
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        status = "activated" if user.is_active else "deactivated"
        return jsonify({
            "message": f"User {status} successfully",
            "user_id": user_id,
            "is_active": user.is_active
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to toggle user status: {str(e)}"}), 500
