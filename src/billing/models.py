from uuid import uuid4, UUID as PyUUID
from enum import Enum
from datetime import timezone, datetime
from src.database import Base
from sqlalchemy import String, DateTime, ForeignKey, Integer, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    TRAILAING = "trialing"
    CANCELED = "canceled"
    PAST_DUE = "past_due"

class BillingPeriod(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentProvider(str, Enum):
    MANUAL = "manual"
    STRIPE = "stripe"
    PAYMOB = "paymob"


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default= uuid4)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(100), unique=True)
    price_cents: Mapped[int] = mapped_column(Integer())
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    billing_period: Mapped[BillingPeriod] = mapped_column(SAEnum(BillingPeriod))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    stripe_product_id: Mapped[str] = mapped_column(String(), nullable=True)
    stripe_price_id: Mapped[str] = mapped_column(String(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                    default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                default=lambda: datetime.now(timezone.utc),onupdate=lambda: datetime.now(timezone.utc))
    
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")

    


class Subscription(Base):
    __tablename__ = "subscriptions"


    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default= uuid4)
    user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True),
            ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(SAEnum(SubscriptionStatus))
    provider: Mapped[str] = mapped_column(String(), nullable=False)
    provider_subscription_id: Mapped[str] = mapped_column(String(), nullable=True, unique=True)
    provider_customer_id: Mapped[str] = mapped_column(String(), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                    default=lambda: datetime.now(timezone.utc))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)


    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")







