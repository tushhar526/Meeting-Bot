from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.userModel import userModel
from app.models.planModel import PlanType
from app.helper.logger import get_logger

logger = get_logger(__name__)


class PlanConfig:
    """Centralized plan configuration with feature access control"""
    
    # Define available features
    FEATURES = {
        'recording': 'Meeting Recording',
        'streaming': 'Live Streaming',
        'download': 'Download Recordings', 
        'metadata': 'Recording Metadata',
        'analytics': 'Advanced Analytics',
        'api_access': 'API Access',
        'priority_support': 'Priority Support',
        'custom_branding': 'Custom Branding',
        'unlimited_meetings': 'Unlimited Meetings',
        'cloud_storage': 'Cloud Storage',
        'transcription': 'Meeting Transcription',
        'multi_platform': 'Multi-Platform Support'
    }
    
    # Plan configurations with differentiated features
    PLAN_FEATURES = {
        PlanType.FREE: {
            'recording': True,
            'streaming': False,
            'download': True,
            'metadata': True,
            'analytics': False,
            'api_access': False,
            'priority_support': False,
            'custom_branding': False,
            'unlimited_meetings': False,
            'cloud_storage': False,
            'transcription': False,
            'multi_platform': False,
            'max_meetings': 5,
            'storage_limit_mb': 100
        },
        PlanType.BASIC: {
            'recording': True,
            'streaming': True,
            'download': True,
            'metadata': True,
            'analytics': True,
            'api_access': False,
            'priority_support': False,
            'custom_branding': False,
            'unlimited_meetings': False,
            'cloud_storage': True,
            'transcription': False,
            'multi_platform': True,
            'max_meetings': 50,
            'storage_limit_mb': 1000
        },
        PlanType.PRO: {
            'recording': True,
            'streaming': True,
            'download': True,
            'metadata': True,
            'analytics': True,
            'api_access': True,
            'priority_support': True,
            'custom_branding': False,
            'unlimited_meetings': False,
            'cloud_storage': True,
            'transcription': True,
            'multi_platform': True,
            'max_meetings': 200,
            'storage_limit_mb': 5000
        },
        PlanType.ENTERPRISE: {
            'recording': True,
            'streaming': True,
            'download': True,
            'metadata': True,
            'analytics': True,
            'api_access': True,
            'priority_support': True,
            'custom_branding': True,
            'unlimited_meetings': True,
            'cloud_storage': True,
            'transcription': True,
            'multi_platform': True,
            'max_meetings': None,  # Unlimited
            'storage_limit_mb': None  # Unlimited
        }
    }
    
    @classmethod
    def get_plan_features(cls, plan_type):
        """Get all features for a plan type"""
        return cls.PLAN_FEATURES.get(plan_type, {})
    
    @classmethod
    def has_feature_access(cls, plan_type, feature):
        """Check if a plan type has access to a specific feature"""
        plan_config = cls.get_plan_features(plan_type)
        return plan_config.get(feature, False)
    
    @classmethod
    def get_plan_limits(cls, plan_type):
        """Get plan limits (meetings, storage, etc.)"""
        plan_config = cls.get_plan_features(plan_type)
        return {
            'max_meetings': plan_config.get('max_meetings'),
            'storage_limit_mb': plan_config.get('storage_limit_mb'),
            'unlimited_meetings': plan_config.get('unlimited_meetings', False)
        }
    
    @classmethod
    def get_available_features(cls):
        """Get list of all available features"""
        return list(cls.FEATURES.keys())
    
    @classmethod
    def get_feature_display_name(cls, feature):
        """Get display name for a feature"""
        return cls.FEATURES.get(feature, feature.title())
    
    @classmethod
    def get_plan_comparison(cls):
        """Get comparison matrix of all plans"""
        comparison = {}
        for plan_type in PlanType:
            plan_features = cls.get_plan_features(plan_type)
            comparison[plan_type.value] = {
                feature: plan_features.get(feature, False) 
                for feature in cls.FEATURES.keys()
            }
        return comparison


def require_plan_access(required_feature=None):
    """
    Decorator to enforce plan-based access control
    
    Args:
        required_feature: Optional specific feature required (e.g., 'recording', 'streaming')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                user_id = get_jwt_identity()
                logger.info(f"Plan access check for user {user_id}, feature: {required_feature}")
                
                user = userModel.query.filter_by(user_id=user_id).first()
                
                if not user:
                    logger.warning(f"Plan access denied - user not found: {user_id}")
                    return jsonify({"error": "User not found"}), 404
                
                if not user.is_active:
                    logger.warning(f"Plan access denied - inactive user: {user_id}")
                    return jsonify({"error": "User account is inactive"}), 403
                
                # Super admins have access to everything
                if user.is_super_admin():
                    logger.info(f"Plan access granted - super admin: {user_id}")
                    return f(*args, **kwargs)
                
                # Check if user has an active plan
                if not user.has_active_subscription():
                    logger.warning(f"Plan access denied - no active subscription: {user_id}")
                    return jsonify({"error": "Active subscription required"}), 403
                
                # Get user's plan
                if not user.plan:
                    logger.warning(f"Plan access denied - no plan assigned: {user_id}")
                    return jsonify({"error": "No plan assigned"}), 403
                
                if not user.plan.is_active:
                    logger.warning(f"Plan access denied - inactive plan: {user_id}")
                    return jsonify({"error": "Plan is inactive"}), 403
                
                # Check meeting limits
                plan_limits = PlanConfig.get_plan_limits(user.plan.plan_type)
                max_meetings = plan_limits['max_meetings']
                
                if not plan_limits['unlimited_meetings'] and max_meetings is not None:
                    if user.meetings >= max_meetings:
                        logger.warning(f"Plan access denied - meeting limit exceeded: {user_id}")
                        return jsonify({
                            "error": "Meeting limit exceeded",
                            "limit": max_meetings,
                            "current": user.meetings,
                            "plan": user.plan.plan_type.value
                        }), 403
                
                # Check specific feature access based on plan type
                if required_feature:
                    if not PlanConfig.has_feature_access(user.plan.plan_type, required_feature):
                        logger.warning(f"Plan access denied - feature '{required_feature}' not available in {user.plan.plan_type.value} plan for user {user_id}")
                        return jsonify({
                            "error": f"Feature '{required_feature}' not available in {user.plan.plan_type.value} plan",
                            "required_feature": required_feature,
                            "current_plan": user.plan.plan_type.value,
                            "available_features": [
                                feat for feat in PlanConfig.get_available_features() 
                                if PlanConfig.has_feature_access(user.plan.plan_type, feat)
                            ]
                        }), 403
                
                logger.info(f"Plan access granted for user {user_id}")
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Plan access check failed for user {user_id}", exception=e)
                return jsonify({"error": "Access check failed"}), 500
                
        return decorated_function
    return decorator


# Legacy function for backward compatibility
def _has_feature_access(plan_type, feature):
    """Legacy function - use PlanConfig.has_feature_access instead"""
    return PlanConfig.has_feature_access(plan_type, feature)
