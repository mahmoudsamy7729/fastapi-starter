from typing import Annotated
from fastapi import Depends
from src.billing.repository import PlanRepository, SubscriptionRepoistory
from src.database import db_dependency
from src.auth_bearer import user_dependency, non_active_user_dependency
from src.auth.emails import Emails


def get_plan_repo(db: db_dependency) -> PlanRepository:
    return PlanRepository(db)

plan_dependency = Annotated[PlanRepository, Depends(get_plan_repo)]

def get_subscription_repo(db: db_dependency) -> SubscriptionRepoistory:
    return SubscriptionRepoistory(db)

subscription_dependency = Annotated[SubscriptionRepoistory, Depends(get_subscription_repo)]

