import stripe
from fastapi.concurrency import run_in_threadpool
from src.billing.models import Subscription, Plan, PaymentProvider
from src.config import settings
from src.auth.models import User
from src.auth.dependencies import repo_dependency
from src.billing.dependencies import subscription_dependency, plan_dependency


stripe.api_key = settings.stripe_secret_key

def serialize_subscription(subscription: Subscription) -> dict:
    """
    Converts a Subscription SQLAlchemy object into a JSON-serializable dict
    ready to be sent to Celery tasks.
    """
    return {
        "id": subscription.id,
        "user": {
            "email": subscription.user.email,
            "username": subscription.user.username
        },
        "plan": {
            "name": subscription.plan.name,
            "price_cents": subscription.plan.price_cents
        },
        "start_date": subscription.started_at.strftime("%Y-%m-%d"),
        "end_date": subscription.current_period_end.strftime("%Y-%m-%d") 
                    if subscription.current_period_end else None,
        "price": subscription.plan.price_cents / 100
    }



class StripeUtils:
    @staticmethod
    async def save_stripe_plan(plan: Plan):
        try:
            if not plan.stripe_product_id:
                product = await run_in_threadpool(
                    stripe.Product.create,
                    name=plan.name,
                )
                plan.stripe_product_id = product.id

            if not plan.stripe_price_id:
                price = await run_in_threadpool(
                    stripe.Price.create,
                    unit_amount=plan.price_cents,   # in cents
                    currency=plan.currency,
                    recurring={"interval": "month"},
                    product=plan.stripe_product_id,
                )
                plan.stripe_price_id = price.id

            return plan
        
        except stripe.error.StripeError as e:
            # handle Stripe errors
            print(f"Stripe error: {e}")
            return None
    

    @staticmethod
    async def stripe_subscripe_checkout_url(user: User, plan: Plan, user_repo: repo_dependency) -> str | None:
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
            email=user.email
        )
            user = await user_repo.update(user, stripe_customer_id = customer['id'])

        
        session = await run_in_threadpool(
            stripe.checkout.Session.create,
            mode="subscription",
            customer=user.stripe_customer_id,        # optional if you want automatic link to user
            line_items=[{
                "price": plan.stripe_price_id,
                "quantity": 1,
            }],
            success_url="https://yourapp.com/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://yourapp.com/cancel",
            client_reference_id=str(user.id),  
            subscription_data={
                "metadata": {
                    "plan_id": str(plan.id),
                    "plan_code": plan.code,
                    "plan_name": plan.name,
                    "user_id": str(user.id),
                }
            },
        )

        return session.url
    

    @staticmethod
    async def user_subscripe (session, sub_repo: subscription_dependency, plan_repo: plan_dependency) -> Subscription:
        user_id = session.get("client_reference_id")
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        stripe_subscription = await run_in_threadpool(
            stripe.Subscription.retrieve,
            subscription_id,
        )
        sub_metadata = stripe_subscription.get("metadata", {}) or {}
        plan_id = sub_metadata.get("plan_id")
        plan = await plan_repo.get_by_id(plan_id) #type: ignore
        sub = await sub_repo.create_subscription(user_id, plan, PaymentProvider.STRIPE, subscription_id, customer_id)
        return sub


    @staticmethod
    async def handle_invoice_payment_succeeded():
        pass 


    @staticmethod
    async def user_unsubscripe():
        pass
