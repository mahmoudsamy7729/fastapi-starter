from typing import Annotated, Tuple
from fastapi import Depends, HTTPException, status
from src.billing.repository import PlanRepository, SubscriptionRepoistory, PaymentRepository
from src.database import db_dependency
from typing import Callable, Awaitable, Tuple
from src.auth.models import User
from src.billing.models import Subscription, Plan, PlanTier
from src.auth_bearer import user_dependency


def get_plan_repo(db: db_dependency) -> PlanRepository:
    return PlanRepository(db)

plan_dependency = Annotated[PlanRepository, Depends(get_plan_repo)]

def get_subscription_repo(db: db_dependency) -> SubscriptionRepoistory:
    return SubscriptionRepoistory(db)

subscription_dependency = Annotated[SubscriptionRepoistory, Depends(get_subscription_repo)]


def get_payment_repo(db: db_dependency)-> PaymentRepository:
    return PaymentRepository(db)

payment_dependency = Annotated[PaymentRepository, Depends(get_payment_repo)]


def require_plan(min_plan: PlanTier):
    async def _dep(
        user: user_dependency,
        sub_repo: subscription_dependency,
        plan_repo: plan_dependency,
    ) -> Tuple["User", "Subscription", "Plan"]:  # adjust types/imports as needed
        # 1) get active subscription for user
        subscription = await sub_repo.get_subscription_with_access(user.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You need an active subscription to access this resource.",
            )

        # 2) get the plan for that subscription
        plan = await plan_repo.get_by_id(subscription.plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your subscription plan is invalid. Please contact support.",
            )

        # 3) check the tier (FREE < PRO < VIP)
        if plan.tier < min_plan:
            # e.g. endpoint requires PRO, user has FREE
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires {min_plan.name} plan or higher.",
            )

        return user, subscription, plan

    return _dep






