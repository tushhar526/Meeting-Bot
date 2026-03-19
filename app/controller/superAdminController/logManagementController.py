from flask import request, jsonify
from datetime import datetime, timezone, timedelta
from app.models.logModel import SystemLog, LogLevel, LogCategory
from app.models.userModel import userModel
from app.extension import db
from sqlalchemy import func, desc
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class LogManagementController:
    """Controller for system log management by super admins"""
    
    @staticmethod
    def get_client_info():
        """Get client information from request"""
        return {
            'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
            'user_agent': request.headers.get('User-Agent', ''),
            'endpoint': f"{request.method} {request.endpoint}",
            'path': request.path
        }
    
    @staticmethod
    def get_all_logs():
        """Get all system logs with pagination and filtering"""
        try:
            # Get query parameters
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 50, type=int), 100)
            level = request.args.get('level')
            category = request.args.get('category')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            user_id = request.args.get('user_id', type=int)
            
            # Debug logging
            logger.info(f"Filter params - Level: {level}, Category: {category}, Page: {page}")
            
            # Build query
            query = SystemLog.query
            
            # Apply filters (case-insensitive)
            if level:
                query = query.filter(func.lower(SystemLog.level) == level.lower())
            if category:
                query = query.filter(func.lower(SystemLog.category) == category.lower())
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(SystemLog.created_at >= start_dt)
            if end_date:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(SystemLog.created_at <= end_dt)
            if user_id:
                query = query.filter(SystemLog.user_id == user_id)
            
            # Debug: Count total logs before filtering
            total_logs = query.count()
            logger.info(f"Total logs matching filters: {total_logs}")
            
            # Order by most recent
            query = query.order_by(desc(SystemLog.created_at))
            
            # Paginate
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            logs_data = []
            for log in pagination.items:
                log_data = {
                    "log_id": log.id,  # Fixed: use Log.id instead of log.log_id
                    "level": log.level,
                    "category": log.category,
                    "message": log.message,
                    "details": log.details,
                    "user_id": log.user_id,
                    "ip_address": log.ip_address,
                    "endpoint": None,  # Not available in SystemLog model
                    "method": None,  # Not available in SystemLog model
                    "status_code": None,  # Not available in SystemLog model
                    "platform": None,  # Not available in SystemLog model
                    "success": None,   # Not available in SystemLog model
                    "operation": None, # Not available in SystemLog model
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                logs_data.append(log_data)
            
            return jsonify({
                "logs": logs_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching logs: {str(e)}")
            return jsonify({"error": f"Failed to fetch logs: {str(e)}"}), 500
    
    @staticmethod
    def get_log_stats():
        """Get log statistics and analytics"""
        try:
            # Get date range for stats (last 30 days by default)
            days = request.args.get('days', 30, type=int)
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Total logs in period
            total_logs = SystemLog.query.filter(SystemLog.created_at >= start_date).count()
            
            # Logs by level
            level_stats = (
                db.session.query(SystemLog.level, func.count(SystemLog.id))
                .filter(SystemLog.created_at >= start_date)
                .group_by(SystemLog.level)
                .all()
            )
            
            # Logs by category
            category_stats = (
                db.session.query(SystemLog.category, func.count(SystemLog.id))
                .filter(SystemLog.created_at >= start_date)
                .group_by(SystemLog.category)
                .all()
            )
            
            # Recent security events
            security_logs = (
                SystemLog.query.filter_by(category=LogCategory.SECURITY)
                .filter(SystemLog.created_at >= start_date)
                .order_by(desc(SystemLog.created_at))
                .limit(10)
                .all()
            )
            
            # Error rate
            error_logs = SystemLog.query.filter(
                SystemLog.created_at >= start_date,
                SystemLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL])
            ).count()
            
            error_rate = (error_logs / total_logs * 100) if total_logs > 0 else 0
            
            return jsonify({
                "period_days": days,
                "total_logs": total_logs,
                "error_rate": round(error_rate, 2),
                "level_distribution": dict(level_stats),
                "category_distribution": dict(category_stats),
                "recent_security_events": [
                    {
                        "log_id": log.id,
                        "message": log.message,
                        "created_at": log.created_at.isoformat(),
                        "ip_address": log.ip_address
                    }
                    for log in security_logs
                ]
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching log stats: {str(e)}")
            return jsonify({"error": f"Failed to fetch log statistics: {str(e)}"}), 500
    
    @staticmethod
    def get_security_logs():
        """Get security-related logs"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 50, type=int), 100)
            
            security_logs = (
                SystemLog.query.filter_by(category=LogCategory.SECURITY)
                .order_by(desc(SystemLog.created_at))
                .paginate(page=page, per_page=per_page, error_out=False)
            )
            
            logs_data = []
            for log in security_logs.items:
                log_data = {
                    "log_id": log.id,
                    "message": log.message,
                    "details": log.details,
                    "user_id": log.user_id,
                    "ip_address": log.ip_address,
                    "endpoint": None,  # Not available in SystemLog model
                    "method": None,    # Not available in SystemLog model
                    "created_at": log.created_at.isoformat()
                }
                logs_data.append(log_data)
            
            return jsonify({
                "security_logs": logs_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": security_logs.total,
                    "pages": security_logs.pages
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching security logs: {str(e)}")
            return jsonify({"error": f"Failed to fetch security logs: {str(e)}"}), 500
    
    @staticmethod
    def export_logs():
        """Export logs to CSV format"""
        try:
            import csv
            from io import StringIO
            from flask import Response
            
            # Get filters
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            level = request.args.get('level')
            category = request.args.get('category')
            
            # Build query
            query = SystemLog.query
            
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(SystemLog.created_at >= start_dt)
            if end_date:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(SystemLog.created_at <= end_dt)
            if level:
                query = query.filter(SystemLog.level == level)
            if category:
                query = query.filter(SystemLog.category == category)
            
            # Get logs (limit to prevent memory issues)
            logs = query.order_by(desc(SystemLog.created_at)).limit(10000).all()
            
            # Create CSV
            output = StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                'Log ID', 'Level', 'Category', 'Message', 'Details', 
                'User ID', 'IP Address', 'Endpoint', 'Method', 
                'Status Code', 'Created At'
            ])
            
            # Data rows
            for log in logs:
                writer.writerow([
                    log.id,
                    log.level,
                    log.category,
                    log.message,
                    log.details,
                    log.user_id,
                    log.ip_address,
                    None,  # endpoint - not available in SystemLog model
                    None,  # method - not available in SystemLog model
                    None,  # status_code - not available in SystemLog model
                    log.created_at.isoformat() if log.created_at else None
                ])
            
            # Create response
            output.seek(0)
            response = Response(output.getvalue(), mimetype='text/csv')
            response.headers['Content-Disposition'] = f'attachment; filename=system_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
            return response
            
        except Exception as e:
            logger.error(f"Error exporting logs: {str(e)}")
            return jsonify({"error": f"Failed to export logs: {str(e)}"}), 500
    
    @staticmethod
    def clear_old_logs():
        """Clear logs older than specified days"""
        try:
            days = request.json.get('days', 90)
            if days < 30:
                return jsonify({"error": "Cannot delete logs newer than 30 days"}), 400
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            deleted_count = SystemLog.query.filter(SystemLog.created_at < cutoff_date).count()
            SystemLog.query.filter(SystemLog.created_at < cutoff_date).delete()
            db.session.commit()
            
            return jsonify({
                "message": f"Deleted {deleted_count} log entries older than {days} days",
                "cutoff_date": cutoff_date.isoformat()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing old logs: {str(e)}")
            return jsonify({"error": f"Failed to clear logs: {str(e)}"}), 500


# Static method wrappers for route handlers
def get_all_logs_handler():
    return LogManagementController.get_all_logs()


def get_log_stats_handler():
    return LogManagementController.get_log_stats()


def get_security_logs_handler():
    return LogManagementController.get_security_logs()


def export_logs_handler():
    return LogManagementController.export_logs()


def clear_old_logs_handler():
    return LogManagementController.clear_old_logs()
