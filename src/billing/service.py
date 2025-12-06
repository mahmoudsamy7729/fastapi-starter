import stripe
import logging
from uuid import UUID
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from src.config import settings
from src.billing import schemas
from src.billing.models import PaymentProvider
from src.billing.repository import PlanRepository, SubscriptionRepoistory, PaymentRepository
from src.billing.tasks import send_subscription_email_task, send_update_subscription_email_task, send_cancel_subscription_email_task, send_payment_failed_email_task
from src.billing.utils import serialize_subscription
from src.billing.stripe_gateway import StripeGateway
from src.auth.models import User
from src.auth.repository import UserRepository


logger = logging.getLogger(__name__)
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
        stripe_plan = await StripeGateway.save_plan_to_stripe(result)
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
        
        update_data = await StripeGateway.update_plan_in_stripe(plan, data)
        result = await repo.update(plan, update_data)    
        return result
    

    @staticmethod
    async def soft_delete_plan(plan_id: UUID, repo: PlanRepository):
        plan = await repo.get_by_id(plan_id)
        if not plan: 
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan found for this id")
        if not plan.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan already deleted.")
       
        await StripeGateway.soft_delete_plan_in_stripe(plan)
        await repo.soft_delete(plan)
    


class SubscriptionService:
    @staticmethod
    async def get_user_subscription(user_id: UUID, repo: SubscriptionRepoistory):
        subscription = await repo.get_subscription_with_access(user_id)
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found for this user.")
        return subscription
    

    @staticmethod 
    async def subscribe_user_to_plan(user: User, plan_code: str,
        sub_repo: SubscriptionRepoistory, plan_repo: PlanRepository, user_repo: UserRepository):

        exisitng_sub = await sub_repo.get_subscription_with_access(user.id)
        if exisitng_sub:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already has an active subscription.")
        plan = await plan_repo.get_by_code(plan_code)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan found for this code.")
        
        checkout_url = await StripeGateway.create_subscription_checkout_session(user, plan, user_repo)

        return checkout_url

    
    @staticmethod
    async def cancel_subscription_at_end_of_period(user_id: UUID, sub_repo: SubscriptionRepoistory):
        sub = await sub_repo.get_subscription_with_access(user_id)
        if not sub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found for this user.")

        if sub.cancel_at_period_end is True: #type: ignore
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subscription is already set to cancel at the end of the billing period.")
        
        if sub.provider == PaymentProvider.STRIPE:
            canceled_at, current_period_end = await StripeGateway.cancel_subscription_at_period_end(sub)

        updated_sub = await sub_repo.cancel_subscription(
            provider=sub.provider,
            provider_subscription_id=sub.provider_subscription_id,
            canceled_at=canceled_at,
            current_period_end=current_period_end,
        )
        if updated_sub is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found in our database.",
            )

        return updated_sub


    @staticmethod
    async def upgrade_subscription(user: User, new_plan_code: str, sub_repo: SubscriptionRepoistory, 
                            plan_repo: PlanRepository, user_repo: UserRepository) :
        current_sub = await sub_repo.get_subscription_with_access(user.id)
        if not current_sub:
            raise HTTPException(status_code=404, detail="No active subscription to upgrade.")
        
        new_plan = await plan_repo.get_by_code(new_plan_code)
        if not new_plan:
            raise HTTPException(status_code=404, detail="Plan not found.")
        
        if new_plan.id == current_sub.plan_id:
            raise HTTPException(status_code=400, detail="You are already on this plan.")
        
        if current_sub.provider == PaymentProvider.STRIPE:
            checkout_url = await StripeGateway.create_subscription_checkout_session(user, new_plan, user_repo,current_sub.provider_subscription_id)

        return checkout_url


    @staticmethod
    async def stripe_webhook(request, stripe_signature, sub_repo: SubscriptionRepoistory,
        plan_repo: PlanRepository, payment_repo: PaymentRepository):
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
            session = data_object
            sub = await StripeGateway.user_subscribe(session, sub_repo, plan_repo)
            
            
        
        if event_type == "invoice.payment_succeeded":
            invoice = data_object
            billing_reason = invoice.get("billing_reason")
            sub = await StripeGateway.handle_invoice_payment_succeeded(invoice, sub_repo)
            await StripeGateway.record_invoice_payment(invoice, sub, payment_repo)
            if billing_reason == "subscription_cycle":
                send_update_subscription_email_task.delay(serialize_subscription(sub)) #type: ignore
            elif billing_reason == "subscription_create":
                send_subscription_email_task.delay(serialize_subscription(sub)) #type: ignore


        if event_type == "customer.subscription.deleted":
            stripe_subscription = data_object
            sub = await StripeGateway.handle_subscription_deleted(stripe_subscription, sub_repo)
            try:
                send_cancel_subscription_email_task.delay(serialize_subscription(sub))
            except Exception as exc:
                logger.exception("Failed to enqueue cancel subscription email", exc_info=exc)

        
        if event_type == "invoice.payment_failed":
            invoice = data_object
            
            sub = await StripeGateway.handle_invoice_payment_failed(invoice, sub_repo)
            if sub:
                send_payment_failed_email_task.delay(serialize_subscription(sub))



class PaymentService:
    @staticmethod
    async def get_my_payments(user: User, payment_repo: PaymentRepository):
        payments = await payment_repo.get_my_payments(user.id)
        return payments