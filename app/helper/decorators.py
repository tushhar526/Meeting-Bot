import time
import logging
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.userModel import userModel, UserRole, SubscriptionStatus

logger = logging.getLogger(__name__)


def retry(times=3, delay=5, backoff=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, times + 1):
                try:
                    # Add attempt info to kwargs only if function supports it
                    import inspect
                    sig = inspect.signature(func)
                    if '_attempt' in sig.parameters and '_max_attempts' in sig.parameters:
                        kwargs['_attempt'] = attempt
                        kwargs['_max_attempts'] = times
                    
                    result = func(*args, **kwargs)

                    if result is False:
                        logger.warning(
                            f"Attempt {attempt}/{times}: {func.__name__} returned False"
                        )

                        if attempt == times:
                            return False

                        current_delay = delay * (backoff ** (attempt - 1))
                        logger.info(
                            f"Retrying {func.__name__} in {current_delay}s... "
                            f"(Attempt {attempt}/{times})"
                        )
                        time.sleep(current_delay)
                        continue

                    if attempt > 1:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt}/{times}"
                        )
                    return result

                except Exception as e:
                    last_exception = e
                    logger.error(
                        f"Attempt {attempt}/{times}: {func.__name__} failed with {type(e).__name__}: {e}"
                    )

                    if attempt == times:
                        logger.error(f"All {times} attempts failed for {func.__name__}")
                        return False

                    current_delay = delay * (backoff ** (attempt - 1))
                    logger.info(
                        f"Retrying {func.__name__} in {current_delay}s... "
                        f"(Attempt {attempt}/{times})"
                    )
                    time.sleep(current_delay)

            return False

        return wrapper

    return decorator


def require_auth(f):
    """Decorator to require JWT authentication.
    Must be used after @jwt_required() — does NOT call verify_jwt_in_request() again."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # jwt_required() upstream already verified the token; just read the identity.
            user_id = get_jwt_identity()
            user = userModel.get_active_users().filter_by(user_id=int(user_id)).first()

            if not user or not user.is_active:
                return jsonify({"message": "User not found or inactive"}), 401

            return f(user, *args, **kwargs)
        except Exception as e:
            logger.error(f"require_auth error: {e}")
            return jsonify({"message": "Authentication required"}), 401

    return decorated_function


def require_super_admin(f):
    """Decorator to require super admin role.
    Must be used after @jwt_required() — does NOT call verify_jwt_in_request() again."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            user = userModel.get_active_users().filter_by(user_id=int(user_id)).first()

            if not user or not user.is_active:
                return jsonify({"message": "User not found or inactive"}), 401

            if not user.is_super_admin():
                return jsonify({"message": "Super admin access required"}), 403

            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"require_super_admin error: {e}")
            return jsonify({"message": "Authentication required"}), 401

    return decorated_function


def require_admin(f):
    """Decorator to require admin role (or super admin).
    Must be used after @jwt_required() — does NOT call verify_jwt_in_request() again."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            user = userModel.get_active_users().filter_by(user_id=int(user_id)).first()

            if not user or not user.is_active:
                return jsonify({"message": "User not found or inactive"}), 401

            if not (user.is_admin() or user.is_super_admin()):
                return jsonify({"message": "Admin access required"}), 403

            return f(user, *args, **kwargs)
        except Exception as e:
            logger.error(f"require_admin error: {e}")
            return jsonify({"message": "Authentication required"}), 401

    return decorated_function


def require_active_subscription(f):
    """Decorator to require active subscription (except for super admin).
    Must be used after @jwt_required() — does NOT call verify_jwt_in_request() again."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            user = userModel.get_active_users().filter_by(user_id=int(user_id)).first()

            if not user or not user.is_active:
                return jsonify({"message": "User not found or inactive"}), 401

            # Super admins bypass subscription check
            if user.is_super_admin():
                return f(user, *args, **kwargs)

            if not user.has_active_subscription():
                return jsonify({"message": "Active subscription required"}), 403

            return f(user, *args, **kwargs)
        except Exception as e:
            logger.error(f"require_active_subscription error: {e}")
            return jsonify({"message": "Authentication required"}), 401

    return decorated_function
