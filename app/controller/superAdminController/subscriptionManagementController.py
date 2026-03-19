from flask import jsonify, request
from app.extension import db
from app.models.userModel import userModel, UserRole, SubscriptionStatus
from app.models.planModel import PlanModel
from app.schema.userSchema import UserResponse, UserSubscriptionUpdate
from pydantic import ValidationError
from datetime import datetime, timezone
from sqlalchemy import func


def get_all_users_subscriptions():
    """Get all users with their subscription details"""
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


def assign_subscription(user_id):
    """Assign or update subscription for a user"""
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


def cancel_user_subscription(user_id):
    """Cancel user subscription"""
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


def get_subscription_stats():
    """Get subscription statistics"""
    try:
        total_users = userModel.get_active_users().count()
        active_subscriptions = userModel.get_active_users().filter_by(subscription_status=SubscriptionStatus.ACTIVE).count()
        inactive_subscriptions = userModel.get_active_users().filter_by(subscription_status=SubscriptionStatus.INACTIVE).count()
        expired_subscriptions = userModel.get_active_users().filter_by(subscription_status=SubscriptionStatus.EXPIRED).count()
        cancelled_subscriptions = userModel.get_active_users().filter_by(subscription_status=SubscriptionStatus.CANCELLED).count()
        
        # Count users by plan
        plan_stats = []
        plans = PlanModel.query.filter_by(is_active=True).all()
        for plan in plans:
            users_count = userModel.get_active_users().filter_by(plan_id=plan.plan_id).count()
            plan_stats.append({
                "plan_id": plan.plan_id,
                "plan_name": plan.name,
                "plan_type": plan.plan_type,
                "users_count": users_count,
                "price": float(plan.price)
            })

        # Revenue calculation (active subscriptions)
        total_revenue = 0
        for plan_stat in plan_stats:
            plan = next((p for p in plans if p.plan_id == plan_stat["plan_id"]), None)
            if plan:
                total_revenue += plan_stat["users_count"] * float(plan.price)

        # Recent subscription changes (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        recent_changes = db.session.query(
            func.date(userModel.updated_at).label('date'),
            func.count(userModel.user_id).label('count')
        ).filter(
            userModel.updated_at >= thirty_days_ago,
            userModel.subscription_status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED])
        ).group_by(func.date(userModel.updated_at)).order_by(func.date(userModel.updated_at)).all()

        return jsonify({
            "total_users": total_users,
            "subscription_status_breakdown": {
                "active": active_subscriptions,
                "inactive": inactive_subscriptions,
                "expired": expired_subscriptions,
                "cancelled": cancelled_subscriptions
            },
            "plan_distribution": plan_stats,
            "total_monthly_revenue": round(total_revenue, 2),
            "recent_changes": [
                {
                    "date": str(change.date),
                    "changes": change.count
                }
                for change in recent_changes
            ]
        }), 200
    except Exception as e:
        return jsonify({"message": "Error fetching statistics"}), 500


def bulk_subscription_update():
    """Update multiple subscriptions at once"""
    try:
        data = request.json
        user_ids = data.get('user_ids', [])
        updates = data.get('updates', {})
        
        if not user_ids:
            return jsonify({"error": "user_ids is required"}), 400
        
        if not updates:
            return jsonify({"error": "updates is required"}), 400
        
        updated_users = []
        
        for user_id in user_ids:
            user = userModel.query.filter_by(user_id=user_id).first()
            if not user:
                continue
            
            # Apply updates
            if 'plan_id' in updates:
                plan = PlanModel.query.filter_by(plan_id=updates['plan_id']).first()
                if plan:
                    user.assign_plan(plan=plan)
            
            if 'subscription_status' in updates:
                user.subscription_status = updates['subscription_status']
            
            if 'subscription_end_date' in updates:
                if updates['subscription_end_date']:
                    user.subscription_end_date = datetime.fromisoformat(updates['subscription_end_date'])
                else:
                    user.subscription_end_date = None
            
            user.updated_at = datetime.now(timezone.utc)
            updated_users.append(user_id)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Updated {len(updated_users)} subscriptions",
            "updated_user_ids": updated_users
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to bulk update subscriptions: {str(e)}"}), 500


def get_expiring_subscriptions():
    """Get subscriptions expiring soon"""
    try:
        days = request.args.get('days', 30, type=int)
        expiry_date = datetime.now(timezone.utc) + timedelta(days=days)
        
        expiring_users = (
            userModel.get_active_users()
            .filter(
                userModel.subscription_status == SubscriptionStatus.ACTIVE,
                userModel.subscription_end_date <= expiry_date,
                userModel.subscription_end_date >= datetime.now(timezone.utc)
            )
            .order_by(userModel.subscription_end_date)
            .all()
        )
        
        users_data = []
        for user in expiring_users:
            user_data = {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "organization_name": user.organization_name,
                "subscription_end_date": user.subscription_end_date.isoformat(),
                "days_until_expiry": (user.subscription_end_date - datetime.now(timezone.utc)).days,
                "plan": user.plan.to_dict() if user.plan else None
            }
            users_data.append(user_data)
        
        return jsonify({
            "expiring_subscriptions": users_data,
            "total_count": len(users_data),
            "days_threshold": days
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get expiring subscriptions: {str(e)}"}), 500


def extend_subscription(user_id):
    """Extend a user's subscription"""
    try:
        user = userModel.query.filter_by(user_id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.json
        days = data.get('days', 30)
        new_end_date = data.get('new_end_date')
        
        if not user.subscription_end_date:
            return jsonify({"error": "User has no subscription end date"}), 400
        
        if new_end_date:
            user.subscription_end_date = datetime.fromisoformat(new_end_date)
        else:
            user.subscription_end_date = user.subscription_end_date + timedelta(days=days)
        
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            "message": "Subscription extended successfully",
            "new_end_date": user.subscription_end_date.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to extend subscription: {str(e)}"}), 500
