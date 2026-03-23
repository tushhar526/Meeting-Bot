from flask import Blueprint, request, jsonify
import logging
from datetime import datetime, timezone, timedelta
from app.helper.decorators import require_super_admin
from app.models.logModel import SystemLog, LogLevel, LogCategory
from app.extension import db
from sqlalchemy import desc, and_, or_, func

logger = logging.getLogger(__name__)

log_bp = Blueprint('logs', __name__, url_prefix="/logs")

def apply_log_filters(query, level=None, category=None, start_date=None, end_date=None, user_id=None):
    """Apply comprehensive filters to log query"""
    
    # Level filter (case-insensitive)
    if level:
        if isinstance(level, str) and ',' in level:
            # Multiple levels (comma-separated)
            levels = [l.strip().lower() for l in level.split(',') if l.strip()]
            query = query.filter(func.lower(SystemLog.level).in_(levels))
        else:
            # Single level (case-insensitive)
            query = query.filter(func.lower(SystemLog.level) == level.lower())
    
    # Category filter (case-insensitive)
    if category:
        if isinstance(category, str) and ',' in category:
            # Multiple categories (comma-separated)
            categories = [c.strip().lower() for c in category.split(',') if c.strip()]
            query = query.filter(func.lower(SystemLog.category).in_(categories))
        else:
            # Single category (case-insensitive)
            query = query.filter(func.lower(SystemLog.category) == category.lower())
    
    # Date range filter
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(SystemLog.created_at >= start_dt)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(SystemLog.created_at <= end_dt)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    # User filter
    if user_id:
        try:
            user_id = int(user_id)
            query = query.filter(SystemLog.user_id == user_id)
        except ValueError:
            pass  # Invalid user_id, ignore filter
    
    return query


@log_bp.route('/system', methods=['GET'])
@require_super_admin
def get_system_logs():
    """Get system-level logs with comprehensive filtering"""
    try:
        # Get query parameters
        level = request.args.get('level')
        category = request.args.get('category')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')
        limit = min(int(request.args.get('limit', 50)), 1000)  # Cap at 1000
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        # Build base query
        query = SystemLog.query
        
        # Debug: Check total logs before filtering
        total_before = query.count()
        logger.info(f"DEBUG: Total logs before filtering: {total_before}")
        
        # Apply filters
        query = apply_log_filters(query, level, category, start_date, end_date, user_id)
        
        # Debug: Check query after filtering
        total_after = query.count()
        logger.info(f"DEBUG: Total logs after filtering: {total_after}")
        logger.info(f"DEBUG: Filters applied - level: {level}, category: {category}")
        
        # Debug: Show actual query
        logger.info(f"DEBUG: SQL Query: {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
        
        # Order by most recent
        query = query.order_by(desc(SystemLog.created_at))
        
        # Handle pagination vs simple limit
        if page and per_page:
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            logs = pagination.items
            total = pagination.total
            has_next = pagination.has_next
            has_prev = pagination.has_prev
        else:
            logs = query.limit(limit).all()
            total = len(logs)
            has_next = has_prev = False
        
        logger.info(f"DEBUG: Returning {len(logs)} logs")
        
        return jsonify({
            "success": True,
            "logs": [log.to_dict() for log in logs],
            "count": len(logs),
            "total": total,
            "filters": {
                "level": level,
                "category": category,
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "limit": limit,
                "page": page,
                "per_page": per_page
            },
            "pagination": {
                "has_next": has_next,
                "has_prev": has_prev,
                "current_page": page,
                "per_page": per_page
            } if page and per_page else None
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch system logs: {e}")
        return jsonify({"error": "Failed to fetch logs"}), 500

@log_bp.route('/auth', methods=['GET'])
@require_super_admin
def get_auth_logs():
    """Get authentication-related logs with comprehensive filtering"""
    try:
        # Get query parameters
        level = request.args.get('level')
        category = request.args.get('category', 'auth')  # Default to auth category
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')
        limit = min(int(request.args.get('limit', 100)), 1000)
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        # Build base query
        query = SystemLog.query
        
        # Apply filters
        query = apply_log_filters(query, level, category, start_date, end_date, user_id)
        
        # Order by most recent
        query = query.order_by(desc(SystemLog.created_at))
        
        # Handle pagination vs simple limit
        if page and per_page:
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            logs = pagination.items
            total = pagination.total
            has_next = pagination.has_next
            has_prev = pagination.has_prev
        else:
            logs = query.limit(limit).all()
            total = len(logs)
            has_next = has_prev = False
        
        return jsonify({
            "success": True,
            "logs": [log.to_dict() for log in logs],
            "count": len(logs),
            "total": total,
            "category": "authentication",
            "filters": {
                "level": level,
                "category": category,
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "limit": limit,
                "page": page,
                "per_page": per_page
            },
            "pagination": {
                "has_next": has_next,
                "has_prev": has_prev,
                "current_page": page,
                "per_page": per_page
            } if page and per_page else None
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch auth logs: {e}")
        return jsonify({"error": "Failed to fetch logs"}), 500

@log_bp.route('/calendar', methods=['GET'])
@require_super_admin
def get_calendar_logs():
    """Get calendar integration logs with comprehensive filtering"""
    try:
        # Get query parameters
        level = request.args.get('level')
        category = request.args.get('category', 'calendar')  # Default to calendar category
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')
        platform = request.args.get('platform')  # Additional platform filter
        limit = min(int(request.args.get('limit', 100)), 1000)
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        # Build base query
        query = SystemLog.query
        
        # Apply filters
        query = apply_log_filters(query, level, category, start_date, end_date, user_id)
        
        # Additional platform filter in details
        if platform:
            query = query.filter(SystemLog.details.ilike(f'%{platform}%'))
        
        # Order by most recent
        query = query.order_by(desc(SystemLog.created_at))
        
        # Handle pagination vs simple limit
        if page and per_page:
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            logs = pagination.items
            total = pagination.total
            has_next = pagination.has_next
            has_prev = pagination.has_prev
        else:
            logs = query.limit(limit).all()
            total = len(logs)
            has_next = has_prev = False
        
        return jsonify({
            "success": True,
            "logs": [log.to_dict() for log in logs],
            "count": len(logs),
            "total": total,
            "category": "calendar",
            "filters": {
                "level": level,
                "category": category,
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "platform": platform,
                "limit": limit,
                "page": page,
                "per_page": per_page
            },
            "pagination": {
                "has_next": has_next,
                "has_prev": has_prev,
                "current_page": page,
                "per_page": per_page
            } if page and per_page else None
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch calendar logs: {e}")
        return jsonify({"error": "Failed to fetch logs"}), 500

@log_bp.route('/security', methods=['GET'])
@require_super_admin
def get_security_logs():
    """Get security-related logs with comprehensive filtering"""
    try:
        # Get query parameters
        level = request.args.get('level')
        category = request.args.get('category', 'security')  # Default to security category
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')
        limit = min(int(request.args.get('limit', 100)), 1000)
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        # Build base query
        query = SystemLog.query
        
        # Apply filters
        query = apply_log_filters(query, level, category, start_date, end_date, user_id)
        
        # Order by most recent
        query = query.order_by(desc(SystemLog.created_at))
        
        # Handle pagination vs simple limit
        if page and per_page:
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            logs = pagination.items
            total = pagination.total
            has_next = pagination.has_next
            has_prev = pagination.has_prev
        else:
            logs = query.limit(limit).all()
            total = len(logs)
            has_next = has_prev = False
        
        return jsonify({
            "success": True,
            "logs": [log.to_dict() for log in logs],
            "count": len(logs),
            "total": total,
            "category": "security",
            "filters": {
                "level": level,
                "category": category,
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "limit": limit,
                "page": page,
                "per_page": per_page
            },
            "pagination": {
                "has_next": has_next,
                "has_prev": has_prev,
                "current_page": page,
                "per_page": per_page
            } if page and per_page else None
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch security logs: {e}")
        return jsonify({"error": "Failed to fetch logs"}), 500

@log_bp.route('/api', methods=['GET'])
@require_super_admin
def get_api_logs():
    """Get API error logs with comprehensive filtering"""
    try:
        # Get query parameters
        level = request.args.get('level')
        category = request.args.get('category', 'api')  # Default to api category
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')
        limit = min(int(request.args.get('limit', 100)), 1000)
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        # Build base query
        query = SystemLog.query
        
        # Apply filters
        query = apply_log_filters(query, level, category, start_date, end_date, user_id)
        
        # Order by most recent
        query = query.order_by(desc(SystemLog.created_at))
        
        # Handle pagination vs simple limit
        if page and per_page:
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            logs = pagination.items
            total = pagination.total
            has_next = pagination.has_next
            has_prev = pagination.has_prev
        else:
            logs = query.limit(limit).all()
            total = len(logs)
            has_next = has_prev = False
        
        return jsonify({
            "success": True,
            "logs": [log.to_dict() for log in logs],
            "count": len(logs),
            "total": total,
            "category": "api",
            "filters": {
                "level": level,
                "category": category,
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "limit": limit,
                "page": page,
                "per_page": per_page
            },
            "pagination": {
                "has_next": has_next,
                "has_prev": has_prev,
                "current_page": page,
                "per_page": per_page
            } if page and per_page else None
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch API logs: {e}")
        return jsonify({"error": "Failed to fetch logs"}), 500

@log_bp.route('/database', methods=['GET'])
@require_super_admin
def get_database_logs():
    """Get database error logs with comprehensive filtering"""
    try:
        # Get query parameters
        level = request.args.get('level')
        category = request.args.get('category', 'database')  # Default to database category
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')
        limit = min(int(request.args.get('limit', 100)), 1000)
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        # Build base query
        query = SystemLog.query
        
        # Apply filters
        query = apply_log_filters(query, level, category, start_date, end_date, user_id)
        
        # Order by most recent
        query = query.order_by(desc(SystemLog.created_at))
        
        # Handle pagination vs simple limit
        if page and per_page:
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            logs = pagination.items
            total = pagination.total
            has_next = pagination.has_next
            has_prev = pagination.has_prev
        else:
            logs = query.limit(limit).all()
            total = len(logs)
            has_next = has_prev = False
        
        return jsonify({
            "success": True,
            "logs": [log.to_dict() for log in logs],
            "count": len(logs),
            "total": total,
            "category": "database",
            "filters": {
                "level": level,
                "category": category,
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "limit": limit,
                "page": page,
                "per_page": per_page
            },
            "pagination": {
                "has_next": has_next,
                "has_prev": has_prev,
                "current_page": page,
                "per_page": per_page
            } if page and per_page else None
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch database logs: {e}")
        return jsonify({"error": "Failed to fetch logs"}), 500

@log_bp.route('/user/<int:user_id>', methods=['GET'])
@require_super_admin
def get_user_logs(user_id):
    """Get logs for a specific user with comprehensive filtering"""
    try:
        # Get query parameters
        level = request.args.get('level')
        category = request.args.get('category')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(int(request.args.get('limit', 100)), 1000)
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        
        # Build base query
        query = SystemLog.query
        
        # Apply filters (user_id is automatically included)
        query = apply_log_filters(query, level, category, start_date, end_date, user_id)
        
        # Order by most recent
        query = query.order_by(desc(SystemLog.created_at))
        
        # Handle pagination vs simple limit
        if page and per_page:
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            logs = pagination.items
            total = pagination.total
            has_next = pagination.has_next
            has_prev = pagination.has_prev
        else:
            logs = query.limit(limit).all()
            total = len(logs)
            has_next = has_prev = False
        
        return jsonify({
            "success": True,
            "logs": [log.to_dict() for log in logs],
            "count": len(logs),
            "total": total,
            "user_id": user_id,
            "filters": {
                "level": level,
                "category": category,
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "limit": limit,
                "page": page,
                "per_page": per_page
            },
            "pagination": {
                "has_next": has_next,
                "has_prev": has_prev,
                "current_page": page,
                "per_page": per_page
            } if page and per_page else None
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch user logs: {e}")
        return jsonify({"error": "Failed to fetch logs"}), 500

@log_bp.route('/stats', methods=['GET'])
@require_super_admin
def get_log_stats():
    """Get log statistics with comprehensive filtering"""
    try:
        from sqlalchemy import func
        
        # Get query parameters for filtering stats
        level = request.args.get('level')
        category = request.args.get('category')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')
        days = int(request.args.get('days', 30))  # Default to last 30 days
        
        # If no custom date range, use days parameter
        if not start_date:
            start_date = (datetime.now(timezone.utc) - timedelta(hours=24*days)).isoformat()
        
        # Build base query for stats
        query = SystemLog.query
        
        # Apply filters
        query = apply_log_filters(query, level, category, start_date, end_date, user_id)
        
        # Get counts by level
        level_counts = db.session.query(
            SystemLog.level,
            func.count(SystemLog.id)
        ).filter(
            SystemLog.id.in_(query.with_entities(SystemLog.id))
        ).group_by(SystemLog.level).all()
        
        # Get counts by category
        category_counts = db.session.query(
            SystemLog.category,
            func.count(SystemLog.id)
        ).filter(
            SystemLog.id.in_(query.with_entities(SystemLog.id))
        ).group_by(SystemLog.category).all()
        
        # Get recent activity counts
        now = datetime.now(timezone.utc)
        periods = {
            "last_1h": now - timedelta(hours=1),
            "last_24h": now - timedelta(hours=24),
            "last_7d": now - timedelta(days=7),
            "last_30d": now - timedelta(days=30)
        }
        
        period_counts = {}
        for period_name, start_time in periods.items():
            period_query = SystemLog.query.filter(SystemLog.created_at >= start_time)
            period_query = apply_log_filters(period_query, level, category, None, end_date, user_id)
            period_counts[period_name] = period_query.count()
        
        return jsonify({
            "success": True,
            "stats": {
                "by_level": {level[0]: level[1] for level in level_counts},
                "by_category": {category[0]: category[1] for category in category_counts},
                "period_counts": period_counts,
                "total_filtered": query.count(),
                "total_all": SystemLog.query.count()
            },
            "filters": {
                "level": level,
                "category": category,
                "start_date": start_date,
                "end_date": end_date,
                "user_id": user_id,
                "days": days
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch log stats: {e}")
        return jsonify({"error": "Failed to fetch stats"}), 500

@log_bp.route('/debug', methods=['GET'])
@require_super_admin
def debug_logs():
    """Debug endpoint to check database contents"""
    try:
        # Get all sample logs
        all_logs = SystemLog.query.limit(10).all()
        
        # Get unique levels and categories
        levels = db.session.query(SystemLog.level).distinct().all()
        categories = db.session.query(SystemLog.category).distinct().all()
        
        return jsonify({
            "debug_info": {
                "total_logs": SystemLog.query.count(),
                "sample_logs": [log.to_dict() for log in all_logs],
                "available_levels": [level[0] for level in levels],
                "available_categories": [cat[0] for cat in categories],
                "recent_log": SystemLog.query.order_by(desc(SystemLog.created_at)).first().to_dict() if SystemLog.query.first() else None
            }
        })
        
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@log_bp.route('/export', methods=['GET'])
@require_super_admin
def export_logs():
    """Export logs to CSV with comprehensive filtering"""
    try:
        import csv
        from io import StringIO
        from flask import Response
        
        # Get query parameters
        level = request.args.get('level')
        category = request.args.get('category')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = request.args.get('user_id')
        platform = request.args.get('platform')  # For calendar logs
        limit = min(int(request.args.get('limit', 1000)), 10000)  # Higher limit for export
        
        # Build base query
        query = SystemLog.query
        
        # Apply filters
        query = apply_log_filters(query, level, category, start_date, end_date, user_id)
        
        # Additional platform filter for calendar logs
        if platform:
            query = query.filter(SystemLog.details.ilike(f'%{platform}%'))
        
        # Order by most recent
        query = query.order_by(desc(SystemLog.created_at))
        
        # Get logs
        logs = query.limit(limit).all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'User ID', 'Level', 'Category', 'Message', 
            'Details', 'IP Address', 'User Agent', 'Created At'
        ])
        
        # Data rows
        for log in logs:
            writer.writerow([
                log.id,
                log.user_id,
                log.level,
                log.category,
                log.message,
                log.details,
                log.ip_address,
                log.user_agent,
                log.created_at.isoformat() if log.created_at else ''
            ])
        
        # Create response
        output.seek(0)
        filename = f'logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        # Add filter info to filename if filters applied
        filter_parts = []
        if level:
            filter_parts.append(f'level_{level.replace(",", "_")}')
        if category:
            filter_parts.append(f'cat_{category.replace(",", "_")}')
        if user_id:
            filter_parts.append(f'user_{user_id}')
        if platform:
            filter_parts.append(f'platform_{platform}')
        
        if filter_parts:
            filename = f'logs_{"_".join(filter_parts)}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to export logs: {e}")
        return jsonify({"error": "Failed to export logs"}), 500
