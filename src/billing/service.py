from uuid import UUID
from fastapi import HTTPException, status
from src.billing.repository import PlanRepository, SubscriptionRepoistory
from src.billing import schemas




class PlanService:
    @staticmethod
    async def retrive_plans(repo: PlanRepository):
        plans = await repo.list_plans()
        return plans
    

    @staticmethod
    async def create_plan(data: schemas.PlanCreate, repo: PlanRepository):
        existing_code = await repo.get_by_code(data.code)
        if existing_code :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Existing Code")
        result = await repo.create(data.model_dump())
        return result


    @staticmethod
    async def get_plan_by_id(plan_id: UUID, repo: PlanRepository):
        plan = await repo.get_by_id(plan_id)
        if not plan: 
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan found for this id")
        return plan
    

    @staticmethod
    async def update_plan(plan_id: UUID, data: schemas.PlanUpdate, repo: PlanRepository):
        plan = await repo.get_by_id(plan_id)
        if not plan: 
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan found for this id")
        result = await repo.update(plan, data.model_dump(exclude_unset=True))    
        return result
    

    @staticmethod
    async def soft_delete_plan(plan_id: UUID, repo: PlanRepository):
        plan = await repo.get_by_id(plan_id)
        if not plan: 
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan found for this id")
        if not plan.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan already deleted.")
       
        await repo.soft_delete(plan)
    


class SubscriptionService:
    @staticmethod
    async def get_user_subscription(user_id: UUID, repo: SubscriptionRepoistory):
        subscription = await repo.get_active_for_user(user_id)
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found for this user.")
        return subscription
    

    @staticmethod 
    async def subscribe_user_to_plan(user_id: UUID, plan_code: str,
                                    sub_repo: SubscriptionRepoistory, plan_repo: PlanRepository):
        exisitng_sub = await sub_repo.get_active_for_user(user_id)
        if exisitng_sub:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has an active subscription.")
        plan = await plan_repo.get_by_code(plan_code)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan found for this code.")
        
        subscription = await sub_repo.create_subscription(user_id, plan)
        return subscription
    

    @staticmethod
    async def cancel_subscription(user_id: UUID, sub_repo: SubscriptionRepoistory):
        subscription = await sub_repo.get_active_for_user(user_id)
        if subscription.cancel_at_period_end is True or not subscription: #type: ignore
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found for this user.")
        await sub_repo.cancel_at_period_end(subscription)
        return subscription
    



    