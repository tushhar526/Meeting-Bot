from app.extension import db
from sqlalchemy import String, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import bcrypt
from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class userModel(db.Model):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    organization_name: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=UserRole.ADMIN)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.plan_id"), nullable=True)
    subscription_status: Mapped[str] = mapped_column(String(50), nullable=False, default=SubscriptionStatus.INACTIVE)
    subscription_start_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    subscription_end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # Soft delete flag
    deleted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    meetings: Mapped[int] = mapped_column(Integer, default=0)

    jobs = relationship("JobModel", back_populates="user")
    plan = relationship("PlanModel", back_populates="users")

    def set_password(self, raw_password):
        hashed = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())
        self.password = hashed.decode("utf-8")

    def check_password(self, raw_password):
        return bcrypt.checkpw(
            raw_password.encode("utf-8"), self.password.encode("utf-8")
        )

    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def has_active_subscription(self):
        return (self.subscription_status == SubscriptionStatus.ACTIVE and 
                self.subscription_end_date and 
                self.subscription_end_date > datetime.utcnow())

    def can_create_meeting(self):
        if self.is_super_admin():
            return True
        return self.has_active_subscription()

    def assign_plan(self, plan, start_date=None, end_date=None):
        """Assign a plan to user with subscription dates"""
        self.plan_id = plan.plan_id
        self.subscription_status = SubscriptionStatus.ACTIVE
        self.subscription_start_date = start_date or datetime.now(timezone.utc)
        self.subscription_end_date = end_date
        self.updated_at = datetime.now(timezone.utc)

    def cancel_subscription(self):
        """Cancel user subscription"""
        self.subscription_status = SubscriptionStatus.CANCELLED
        self.updated_at = datetime.now(timezone.utc)

    def soft_delete(self):
        """Soft delete user - mark as deleted but keep in database"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore soft deleted user"""
        self.is_deleted = False
        self.deleted_at = None
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def get_active_users(cls):
        """Get only non-deleted users"""
        return cls.query.filter_by(is_deleted=False)

    @classmethod
    def get_by_email_or_username(cls, identifier):
        """Get user by email or username (excluding deleted)"""
        return cls.query.filter(
            (cls.email == identifier) | (cls.username == identifier),
            cls.is_deleted == False
        ).first()
