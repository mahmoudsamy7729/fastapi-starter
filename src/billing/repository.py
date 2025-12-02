from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.billing.models import Plan, Subscription, SubscriptionStatus, BillingPeriod


class PlanRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def list_plans(self, active_only: bool = True) -> List[Plan]:
        stmt = select(Plan)
        if active_only:
            stmt = stmt.where(Plan.is_active.is_(True))
        result = await self.db.execute(stmt.order_by(Plan.price_cents))
        return list(result.scalars().all())
    

    async def get_by_id(self, plan_id: UUID) -> Optional[Plan]:
        result = await self.db.execute(
            select(Plan).where(Plan.id == plan_id)
        )
        return result.scalar_one_or_none()
    

    async def get_by_code(self, code: str) -> Optional[Plan]:
        result = await self.db.execute(
            select(Plan).where(Plan.code == code, Plan.is_active.is_(True))
        )
        return result.scalar_one_or_none()
    

    async def create(self, data: dict) -> Plan:
        plan = Plan(**data)
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan
    

    async def update(self, plan: Plan, data: dict) -> Plan:
        for k, v in data.items():
            if v is not None:
                setattr(plan, k, v)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan
    

    async def soft_delete(self, plan: Plan) -> None:
        plan.is_active = False
        await self.db.commit()
    


class SubscriptionRepoistory:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def list_for_user(self, user_id: UUID) -> List[Subscription]:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.started_at.desc())
        )
        return list(result.scalars().all())


    async def get_subscription_with_access(self, user_id: UUID) -> Subscription | None:
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.current_period_end > now,
                Subscription.status.in_(
                    [
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.CANCELED,  # cancel_at_period_end true still allowed
                    ]
                ),
            )
            .order_by(Subscription.current_period_end.desc())
            .options(
                selectinload(Subscription.user),
                selectinload(Subscription.plan),
            )
        )
        return result.scalar_one_or_none()
    

    async def create_subscription(self, user_id: UUID, plan: Plan, provider: str, 
            provider_subscription_id: str, provider_customer_id: str) -> Subscription:
        old_sub = await self.get_active_for_user(user_id)
        if old_sub:
            old_sub.status = SubscriptionStatus.CANCELED

        now = datetime.now(timezone.utc)
        period_delta = (
            timedelta(days=30)
            if plan.billing_period == BillingPeriod.MONTHLY
            else timedelta(days=365)
        )

        sub = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            # provider fields
            provider=provider,
            provider_subscription_id=provider_subscription_id,
            provider_customer_id=provider_customer_id,

            started_at=now,
            current_period_end=now + period_delta,
        )

        self.db.add(sub)
        await self.db.commit()
        await self.db.refresh(sub)

        result = await self.db.execute(
        select(Subscription)
        .where(Subscription.id == sub.id)
        .options(
                selectinload(Subscription.user),
                selectinload(Subscription.plan),
            )
        )
        return result.scalar_one()
    

    async def cancel_at_period_end(self, subscription: Subscription) -> Subscription:
        subscription.cancel_at_period_end = True
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription
    

    async def cancel_immediately(self, subscription: Subscription) -> Subscription:
        subscription.status = SubscriptionStatus.CANCELED
        subscription.current_period_end = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription
    

    async def update_subscription_period(
        self,
        provider: str,
        provider_subscription_id: str,
        current_period_start: datetime,
        current_period_end: datetime
    ) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.provider == provider,
                Subscription.provider_subscription_id == provider_subscription_id,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            print("⚠️ No local subscription found for stripe_subscription_id:", provider_subscription_id)
            return None

        sub.status = SubscriptionStatus.ACTIVE  
        sub.started_at = current_period_start
        sub.current_period_end = current_period_end

        await self.db.commit()
        await self.db.refresh(sub)
        result = await self.db.execute(
        select(Subscription)
        .where(Subscription.id == sub.id)
        .options(
                selectinload(Subscription.user),
                selectinload(Subscription.plan),
            )
        )
        return result.scalar_one()
    

    async def cancel_subscription(
        self,
        provider: str,
        provider_subscription_id: str,
        canceled_at: datetime,
        current_period_end: datetime | None = None,
    ) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.provider == provider,
                Subscription.provider_subscription_id == provider_subscription_id,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            print("⚠️ No local subscription found to cancel:", provider_subscription_id)
            return None

        sub.status = SubscriptionStatus.CANCELED
        sub.canceled_at = canceled_at
        sub.cancel_at_period_end = True

        # لو Stripe بعت آخر فترة اشتراك، حدّثها
        if current_period_end is not None:
            sub.current_period_end = current_period_end

        await self.db.commit()
        await self.db.refresh(sub)

        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.id == sub.id)
            .options(
                selectinload(Subscription.user),
                selectinload(Subscription.plan),
            )
        )
        return result.scalar_one()



    


