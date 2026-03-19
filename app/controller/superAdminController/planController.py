from flask import jsonify, request
from app.extension import db
from app.models.planModel import PlanModel, PlanType
from datetime import datetime, timezone
from pydantic import ValidationError
from typing import Optional


def create_plan():
    """Create a new plan"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'plan_type', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Field '{field}' is required"}), 400
        
        # Check if plan name already exists
        existing_plan = PlanModel.query.filter_by(name=data['name']).first()
        if existing_plan:
            return jsonify({"error": "Plan with this name already exists"}), 400
        
        # Validate plan type
        if data['plan_type'] not in [pt.value for pt in PlanType]:
            return jsonify({"error": "Invalid plan type"}), 400
        
        # Create new plan
        new_plan = PlanModel(
            name=data['name'],
            plan_type=data['plan_type'],
            description=data.get('description', ''),
            price=float(data['price']),
            max_meetings=data.get('max_meetings'),
            max_users=data.get('max_users'),
            features=data.get('features', ''),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(new_plan)
        db.session.commit()
        
        return jsonify({
            "message": "Plan created successfully",
            "plan": new_plan.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create plan: {str(e)}"}), 500


def update_plan(plan_id):
    """Update an existing plan"""
    try:
        plan = PlanModel.query.get(plan_id)
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
        
        data = request.json
        
        # Update allowed fields
        if 'name' in data:
            # Check if new name conflicts with existing plan
            existing_plan = PlanModel.query.filter_by(name=data['name']).first()
            if existing_plan and existing_plan.plan_id != plan_id:
                return jsonify({"error": "Plan with this name already exists"}), 400
            plan.name = data['name']
        
        if 'plan_type' in data:
            if data['plan_type'] not in [pt.value for pt in PlanType]:
                return jsonify({"error": "Invalid plan type"}), 400
            plan.plan_type = data['plan_type']
        
        if 'description' in data:
            plan.description = data['description']
        
        if 'price' in data:
            plan.price = float(data['price'])
        
        if 'max_meetings' in data:
            plan.max_meetings = data['max_meetings']
        
        if 'max_users' in data:
            plan.max_users = data['max_users']
        
        if 'features' in data:
            plan.features = data['features']
        
        if 'is_active' in data:
            plan.is_active = data['is_active']
        
        plan.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            "message": "Plan updated successfully",
            "plan": plan.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update plan: {str(e)}"}), 500


def delete_plan(plan_id):
    """Delete a plan (soft delete by setting is_active=False)"""
    try:
        plan = PlanModel.query.get(plan_id)
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
        
        # Check if any users are currently on this plan
        from app.models.userModel import userModel
        users_on_plan = userModel.query.filter_by(plan_id=plan_id).count()
        if users_on_plan > 0:
            return jsonify({
                "error": "Cannot delete plan with active users",
                "active_users": users_on_plan
            }), 400
        
        # Soft delete by deactivating
        plan.is_active = False
        plan.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({"message": "Plan deactivated successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete plan: {str(e)}"}), 500


def get_all_plans():
    """Get all plans"""
    try:
        plans = PlanModel.query.all()
        return jsonify({
            "plans": [plan.to_dict() for plan in plans],
            "total": len(plans)
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get plans: {str(e)}"}), 500


def get_plan(plan_id):
    """Get a specific plan"""
    try:
        plan = PlanModel.query.get(plan_id)
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
        
        return jsonify({"plan": plan.to_dict()}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to get plan: {str(e)}"}), 500


def get_active_plans():
    """Get only active plans for public access"""
    try:
        plans = PlanModel.query.filter_by(is_active=True).all()
        return jsonify({
            "plans": [plan.to_dict() for plan in plans]
        }), 200
    except Exception as e:
        return jsonify({"message": "Error fetching plans"}), 500
