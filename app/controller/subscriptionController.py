from flask import jsonify, request
from app.extension import db
from app.models.userModel import userModel, UserRole, SubscriptionStatus
from app.models.planModel import PlanModel
from app.schema.userSchema import UserResponse, UserSubscriptionUpdate
from app.schema.planSchema import PlanResponse, PlanCreate, PlanUpdate
from app.helper.decorators import require_super_admin, require_auth
from pydantic import ValidationError
from datetime import datetime, timedelta
import json


def get_all_plans():
    """Get all available plans"""
    try:
        plans = PlanModel.query.filter_by(is_active=True).all()
        return jsonify({
            "plans": [plan.to_dict() for plan in plans]
        }), 200
    except Exception as e:
        return jsonify({"message": "Error fetching plans"}), 500


@require_super_admin
def create_plan(user):
    """Create a new plan (super admin only)"""
    try:
        try:
            plan_data = PlanCreate(**request.json)
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400

        # Convert features list to JSON string
        features_json = json.dumps(plan_data.features) if plan_data.features else None

        new_plan = PlanModel(
            name=plan_data.name,
            plan_type=plan_data.plan_type,
            description=plan_data.description,
            price=plan_data.price,
            max_meetings=plan_data.max_meetings,
            max_users=plan_data.max_users,
            features=features_json
        )

        db.session.add(new_plan)
        db.session.commit()

        return jsonify({
            "message": "Plan created successfully",
            "plan": new_plan.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error creating plan"}), 500


@require_super_admin
def update_plan(user, plan_id):
    """Update an existing plan (super admin only)"""
    try:
        plan = PlanModel.query.filter_by(plan_id=plan_id).first()
        if not plan:
            return jsonify({"message": "Plan not found"}), 404

        try:
            plan_data = PlanUpdate(**request.json)
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400

        # Update fields if provided
        if plan_data.name is not None:
            plan.name = plan_data.name
        if plan_data.plan_type is not None:
            plan.plan_type = plan_data.plan_type
        if plan_data.description is not None:
            plan.description = plan_data.description
        if plan_data.price is not None:
            plan.price = plan_data.price
        if plan_data.max_meetings is not None:
            plan.max_meetings = plan_data.max_meetings
        if plan_data.max_users is not None:
            plan.max_users = plan_data.max_users
        if plan_data.features is not None:
            plan.features = json.dumps(plan_data.features)
        if plan_data.is_active is not None:
            plan.is_active = plan_data.is_active

        plan.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "message": "Plan updated successfully",
            "plan": plan.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating plan"}), 500


@require_super_admin
def delete_plan(user, plan_id):
    """Delete a plan (super admin only)"""
    try:
        plan = PlanModel.query.filter_by(plan_id=plan_id).first()
        if not plan:
            return jsonify({"message": "Plan not found"}), 404

        # Check if any users are subscribed to this plan
        users_count = userModel.query.filter_by(plan_id=plan_id).count()
        if users_count > 0:
            return jsonify({
                "message": f"Cannot delete plan. {users_count} users are subscribed to this plan."
            }), 400

        db.session.delete(plan)
        db.session.commit()

        return jsonify({"message": "Plan deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error deleting plan"}), 500


@require_super_admin
def get_all_users_subscriptions(user):
    """Get all users with their subscription details (super admin only)"""
    try:
        users = userModel.get_active_users().all()
        users_data = []
        
        for user_obj in users:
            user_dict = UserResponse.model_validate(user_obj).model_dump()
            if user_obj.plan:
                user_dict['plan'] = user_obj.plan.to_dict()
            users_data.append(user_dict)
        
        return jsonify({
            "users": users_data
        }), 200
    except Exception as e:
        return jsonify({"message": "Error fetching users"}), 500


@require_super_admin
def assign_subscription(user, user_id):
    """Assign or update subscription for a user (super admin only)"""
    try:
        target_user = userModel.query.filter_by(user_id=user_id).first()
        if not target_user:
            return jsonify({"message": "User not found"}), 404

        try:
            subscription_data = UserSubscriptionUpdate(**request.json)
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400

        # Update subscription details
        if subscription_data.plan_id is not None:
            plan = PlanModel.query.filter_by(plan_id=subscription_data.plan_id).first()
            if not plan:
                return jsonify({"message": "Plan not found"}), 404
            
            target_user.assign_plan(
                plan=plan,
                end_date=subscription_data.subscription_end_date
            )

        if subscription_data.subscription_status is not None:
            target_user.subscription_status = subscription_data.subscription_status

        db.session.commit()

        user_response = UserResponse.model_validate(target_user)
        if target_user.plan:
            user_response.plan = target_user.plan.to_dict()

        return jsonify({
            "message": "Subscription updated successfully",
            "user": user_response.model_dump()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating subscription"}), 500


@require_super_admin
def cancel_user_subscription(user, user_id):
    """Cancel user subscription (super admin only)"""
    try:
        target_user = userModel.query.filter_by(user_id=user_id).first()
        if not target_user:
            return jsonify({"message": "User not found"}), 404

        target_user.cancel_subscription()
        db.session.commit()

        return jsonify({
            "message": "Subscription cancelled successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error cancelling subscription"}), 500


@require_auth
def get_my_subscription(user):
    """Get current user's subscription details"""
    try:
        user_response = UserResponse.model_validate(user)
        if user.plan:
            user_response.plan = user.plan.to_dict()
        
        return jsonify({
            "user": user_response.model_dump()
        }), 200
    except Exception as e:
        return jsonify({"message": "Error fetching subscription"}), 500


@require_super_admin
def get_subscription_stats(user):
    """Get subscription statistics (super admin only)"""
    try:
        total_users = userModel.get_active_users().count()
        active_subscriptions = userModel.get_active_users().filter_by(subscription_status=SubscriptionStatus.ACTIVE).count()
        inactive_subscriptions = userModel.get_active_users().filter_by(subscription_status=SubscriptionStatus.INACTIVE).count()
        
        # Count users by plan
        plan_stats = []
        plans = PlanModel.query.filter_by(is_active=True).all()
        for plan in plans:
            users_count = userModel.get_active_users().filter_by(plan_id=plan.plan_id).count()
            plan_stats.append({
                "plan_id": plan.plan_id,
                "plan_name": plan.name,
                "users_count": users_count
            })

        return jsonify({
            "total_users": total_users,
            "active_subscriptions": active_subscriptions,
            "inactive_subscriptions": inactive_subscriptions,
            "plan_distribution": plan_stats
        }), 200
    except Exception as e:
        return jsonify({"message": "Error fetching statistics"}), 500


@require_super_admin
def soft_delete_user(user, user_id):
    """Soft delete a user (super admin only)"""
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


@require_super_admin
def restore_user(user, user_id):
    """Restore a soft deleted user (super admin only)"""
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


@require_super_admin
def get_deleted_users(user):
    """Get all soft deleted users (super admin only)"""
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
