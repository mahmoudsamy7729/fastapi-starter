from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from src.billing.models import BillingPeriod, SubscriptionStatus, PaymentStatus, PaymentProvider, Plan




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


class PlanOut(BaseModel):
    id: UUID
    name: str
    code: str
    price_cents: int
    currency: str

    class Config:
        from_attributes = True


class SubscriptionOut(BaseModel):
    id: UUID
    status: SubscriptionStatus  
    started_at: datetime 
    cancel_at_period_end: bool 
    current_period_end: Optional[datetime]
    provider: PaymentProvider
    provider_subscription_id: str
    plan: PlanOut
    
    
    class Config:
        from_attributes = True


class SubscribeRequest(BaseModel):
    plan_code: str


class CheckoutUrlResponse(BaseModel):
    checkout_url: str