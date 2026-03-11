from app.extension import db
from sqlalchemy import String, DateTime, Integer, Boolean, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from enum import Enum


class PlanType(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class PlanModel(db.Model):
    __tablename__ = "plans"

    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.00)
    max_meetings: Mapped[int] = mapped_column(Integer, nullable=True)  # None for unlimited
    max_users: Mapped[int] = mapped_column(Integer, nullable=True)  # None for unlimited
    features: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string of features
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("userModel", back_populates="plan")

    def to_dict(self):
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "plan_type": self.plan_type,
            "description": self.description,
            "price": float(self.price),
            "max_meetings": self.max_meetings,
            "max_users": self.max_users,
            "features": self.features,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
