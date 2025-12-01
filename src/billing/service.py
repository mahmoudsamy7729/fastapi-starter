import stripe
from uuid import UUID
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from src.billing.repository import PlanRepository, SubscriptionRepoistory
from src.auth.repository import UserRepository
from src.billing import schemas
from src.billing.utils import StripeUtils
from src.config import settings
from src.auth.models import User
from src.billing.tasks import send_subscription_email_task
from src.billing.utils import serialize_subscription


stripe.api_key = settings.stripe_secret_key


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
        stripe_plan = await StripeUtils.save_stripe_plan(result)
        if stripe_plan:
            updated_plan = await repo.update(result, {
                "stripe_product_id": stripe_plan.stripe_product_id,
                "stripe_price_id": stripe_plan.stripe_price_id
            })
            return updated_plan
        
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
    async def subscribe_user_to_plan(user: User, plan_code: str,
        sub_repo: SubscriptionRepoistory, plan_repo: PlanRepository, user_repo: UserRepository):

        exisitng_sub = await sub_repo.get_active_for_user(user.id)
        if exisitng_sub:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has an active subscription.")
        plan = await plan_repo.get_by_code(plan_code)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan found for this code.")
        
        checkout_url = await StripeUtils.stripe_subscripe_checkout_url(user, plan, user_repo)

        return checkout_url

    
    @staticmethod
    async def cancel_subscription_at_end_of_period(user_id: UUID, sub_repo: SubscriptionRepoistory):
        subscription = await sub_repo.get_active_for_user(user_id)
        if subscription.cancel_at_period_end is True or not subscription: #type: ignore
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found for this user.")
        await sub_repo.cancel_at_period_end(subscription)
        return subscription
    

    @staticmethod
    async def stripe_webhook(request, stripe_signature, sub_repo: SubscriptionRepoistory,
        plan_repo: PlanRepository):
        payload = await request.body()
        try:
            event = await run_in_threadpool(
                stripe.Webhook.construct_event,
                payload.decode("utf-8"),
                stripe_signature,
                settings.stripe_webhook_secret
            )
        except Exception as e:
            return {"error": str(e)}
        
        event_type = event["type"]
        data_object = event["data"]["object"]

        if event_type == "checkout.session.completed":
            # create subscription in DB
            session = data_object
            sub = await StripeUtils.user_subscripe(session, sub_repo, plan_repo)
            send_subscription_email_task.delay(serialize_subscription(sub)) #type: ignore
        
        if event_type == "invoice.payment_succeeded":
            #Renew the subscription in the db
            invoice = data_object
            


        if event_type == "customer.subscription.deleted":
            #Delete the subscription in the db
            pass

    