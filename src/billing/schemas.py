from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from src.billing.models import BillingPeriod, SubscriptionStatus, PaymentStatus, PaymentProvider




class PlanBase(BaseModel):
    name: str
    code: str
    price_cents: int
    billing_period: BillingPeriod
    currency: str = "USD"
    is_active: bool = True


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    price_cents: Optional[int] = None
    billing_period: Optional[BillingPeriod] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class PlanOut(PlanBase):
    id: UUID

    class Config:
        from_attributes = True


class SubscriptionOut(BaseModel):
    id: UUID
    user_id: UUID
    plan_id: UUID
    status: SubscriptionStatus
    started_at: datetime
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool

    class Config:
        from_attributes = True


class SubscribeRequest(BaseModel):
    plan_code: str

