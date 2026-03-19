from app.extension import db
from sqlalchemy import String, DateTime, Integer, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone, timedelta
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(str, Enum):
    AUTH = "auth"
    CALENDAR = "calendar"
    USER = "user"
    SYSTEM = "system"
    API = "api"
    DATABASE = "database"
    SECURITY = "security"


class SystemLog(db.Model):
    """Model to store system logs and audit trails"""
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=True)
    
    level: Mapped[str] = mapped_column(String(20), nullable=False, default=LogLevel.INFO)
    
    category: Mapped[str] = mapped_column(String(50), nullable=False, default=LogCategory.SYSTEM)
    
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    details: Mapped[str] = mapped_column(Text, nullable=True)
    
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    
    # Relationship back to User
    user = relationship("userModel", back_populates="logs")

    def to_dict(self):
        """Convert log to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def create_log(cls, level: str, category: str, message: str, 
                   user_id: int = None, details: str = None,
                   ip_address: str = None, user_agent: str = None):
        """Create a new log entry"""
        try:
            log = cls(
                level=level,
                category=category,
                message=message,
                details=details,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            # Fallback: try to get Flask app context
            try:
                from flask import current_app
                if current_app:
                    with current_app.app_context():
                        log = cls(
                            level=level,
                            category=category,
                            message=message,
                            details=details,
                            user_id=user_id,
                            ip_address=ip_address,
                            user_agent=user_agent
                        )
                        db.session.add(log)
                        db.session.commit()
                        return log
                else:
                    # No Flask app context available, use standard logging
                    import logging
                    logging.error(f"Failed to create log entry (no Flask context): {message}")
                    return None
            except ImportError:
                # Flask not available, use standard logging
                import logging
                logging.error(f"Failed to create log entry (Flask not available): {message}")
                return None

    @classmethod
    def log_auth_event(cls, message: str, user_id: int = None, 
                      details: str = None, success: bool = True):
        """Log authentication events"""
        level = LogLevel.INFO if success else LogLevel.WARNING
        cls.create_log(
            level=level,
            category=LogCategory.AUTH,
            message=message,
            user_id=user_id,
            details=details
        )

    @classmethod
    def log_calendar_event(cls, message: str, user_id: int = None,
                         platform: str = None, details: str = None,
                         success: bool = True):
        """Log calendar integration events"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        cls.create_log(
            level=level,
            category=LogCategory.CALENDAR,
            message=message,
            user_id=user_id,
            details=f"platform: {platform}, success: {success}, details: {details}"
        )

    @classmethod
    def log_security_event(cls, message: str, user_id: int = None,
                          details: str = None, ip_address: str = None):
        """Log security-related events"""
        cls.create_log(
            level=LogLevel.WARNING,
            category=LogCategory.SECURITY,
            message=message,
            user_id=user_id,
            details=details,
            ip_address=ip_address
        )

    @classmethod
    def log_api_error(cls, message: str, user_id: int = None,
                     endpoint: str = None, method: str = None,
                     status_code: int = None, details: str = None):
        """Log API errors"""
        cls.create_log(
            level=LogLevel.ERROR,
            category=LogCategory.API,
            message=message,
            user_id=user_id,
            details=f"endpoint: {endpoint}, method: {method}, status: {status_code}, details: {details}"
        )

    @classmethod
    def log_database_error(cls, message: str, operation: str = None,
                        details: str = None):
        """Log database errors"""
        cls.create_log(
            level=LogLevel.ERROR,
            category=LogCategory.DATABASE,
            message=message,
            details=f"operation: {operation}, details: {details}"
        )

    @classmethod
    def get_logs_by_user(cls, user_id: int, limit: int = 100):
        """Get logs for a specific user"""
        return cls.query.filter_by(user_id=user_id).order_by(
            cls.created_at.desc()
        ).limit(limit).all()

    @classmethod
    def get_logs_by_level(cls, level: str, limit: int = 100):
        """Get logs by severity level"""
        return cls.query.filter_by(level=level).order_by(
            cls.created_at.desc()
        ).limit(limit).all()

    @classmethod
    def get_logs_by_category(cls, category: str, limit: int = 100):
        """Get logs by category"""
        return cls.query.filter_by(category=category).order_by(
            cls.created_at.desc()
        ).limit(limit).all()

    @classmethod
    def get_recent_logs(cls, limit: int = 50):
        """Get most recent logs"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
