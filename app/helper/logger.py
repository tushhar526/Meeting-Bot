import logging
import traceback
from flask import request
from app.models.logModel import SystemLog, LogLevel, LogCategory
from typing import Optional, Dict, Any


class AppLogger:
    """Centralized logging utility that integrates with SystemLog model"""
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.standard_logger = logging.getLogger(module_name)
    
    def _get_request_info(self) -> Dict[str, Any]:
        """Extract request information for logging"""
        request_info = {}
        try:
            # Check if we're in a request context AND request is available
            from flask import has_request_context, request
            if has_request_context() and request:
                request_info['ip_address'] = request.remote_addr
                request_info['user_agent'] = str(request.user_agent) if request.user_agent else None
            else:
                # Not in request context (e.g., during migrations or startup)
                # Don't try to access request object
                pass
        except Exception:
            # Any error accessing request info
            pass
        return request_info
    
    def _log_to_db(self, level: str, category: str, message: str, 
                   user_id: Optional[int] = None, details: Optional[str] = None,
                   **kwargs):
        """Log to database with error handling"""
        try:
            request_info = self._get_request_info()
            SystemLog.create_log(
                level=level,
                category=category,
                message=message,
                user_id=user_id,
                details=details,
                ip_address=request_info.get('ip_address'),
                user_agent=request_info.get('user_agent')
            )
        except Exception as e:
            # Fallback to standard logging if DB logging fails
            self.standard_logger.error(f"Failed to log to database: {e}")
            # Still log the original message to standard logger
            getattr(self.standard_logger, level.lower(), self.standard_logger.info)(message)
            # Additional check for migration context
            try:
                from flask import has_request_context
                if not has_request_context():
                    self.standard_logger.warning(f"Database logging failed outside request context - message: {message}")
            except ImportError:
                pass
    
    def debug(self, message: str, user_id: Optional[int] = None, details: Optional[str] = None):
        """Log debug message"""
        self.standard_logger.debug(message)
        self._log_to_db(LogLevel.DEBUG, LogCategory.SYSTEM, message, user_id, details)
    
    def info(self, message: str, user_id: Optional[int] = None, details: Optional[str] = None):
        """Log info message"""
        self.standard_logger.info(message)
        self._log_to_db(LogLevel.INFO, LogCategory.SYSTEM, message, user_id, details)
    
    def warning(self, message: str, user_id: Optional[int] = None, details: Optional[str] = None):
        """Log warning message"""
        self.standard_logger.warning(message)
        self._log_to_db(LogLevel.WARNING, LogCategory.SYSTEM, message, user_id, details)
    
    def error(self, message: str, user_id: Optional[int] = None, details: Optional[str] = None, 
              exception: Optional[Exception] = None):
        """Log error message"""
        if exception:
            error_details = f"Exception: {str(exception)}\nTraceback: {traceback.format_exc()}"
            if details:
                details = f"{details}\n{error_details}"
            else:
                details = error_details
        
        self.standard_logger.error(message)
        self._log_to_db(LogLevel.ERROR, LogCategory.SYSTEM, message, user_id, details)
    
    def critical(self, message: str, user_id: Optional[int] = None, details: Optional[str] = None):
        """Log critical message"""
        self.standard_logger.critical(message)
        self._log_to_db(LogLevel.CRITICAL, LogCategory.SYSTEM, message, user_id, details)
    
    # Category-specific logging methods
    def auth(self, message: str, user_id: Optional[int] = None, details: Optional[str] = None, 
             success: bool = True):
        """Log authentication events"""
        level = LogLevel.INFO if success else LogLevel.WARNING
        self.standard_logger.info(f"AUTH: {message}")
        SystemLog.log_auth_event(message, user_id, details, success)
    
    def calendar(self, message: str, user_id: Optional[int] = None, platform: Optional[str] = None, 
                 details: Optional[str] = None, success: bool = True):
        """Log calendar events"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        self.standard_logger.info(f"CALENDAR: {message}")
        SystemLog.log_calendar_event(message, user_id, platform, details, success)
    
    def security(self, message: str, user_id: Optional[int] = None, details: Optional[str] = None):
        """Log security events"""
        self.standard_logger.warning(f"SECURITY: {message}")
        request_info = self._get_request_info()
        SystemLog.log_security_event(message, user_id, details, request_info.get('ip_address'))
    
    def api(self, message: str, user_id: Optional[int] = None, endpoint: Optional[str] = None, 
            method: Optional[str] = None, status_code: Optional[int] = None, 
            details: Optional[str] = None):
        """Log API events"""
        self.standard_logger.info(f"API: {message}")
        SystemLog.log_api_error(message, user_id, endpoint, method, status_code, details)
    
    def database(self, message: str, operation: Optional[str] = None, details: Optional[str] = None):
        """Log database events"""
        self.standard_logger.error(f"DATABASE: {message}")
        SystemLog.log_database_error(message, operation, details)
    
    def meeting(self, message: str, user_id: Optional[int] = None, platform: Optional[str] = None, 
                job_id: Optional[int] = None, details: Optional[str] = None, success: bool = True):
        """Log meeting-related events"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        meeting_details = f"platform: {platform}, job_id: {job_id}, details: {details}"
        self.standard_logger.info(f"MEETING: {message}")
        self._log_to_db(level, LogCategory.CALENDAR, message, user_id, meeting_details)


def get_logger(module_name: str) -> 'AppLogger':
    """Get an AppLogger instance for a module"""
    return AppLogger(module_name)
