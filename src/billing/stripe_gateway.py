import stripe
from datetime import datetime, timezone
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from src.auth.models import User
from src.auth.repository import UserRepository
from src.billing.models import Plan, Subscription, PaymentProvider
from src.billing.dependencies import plan_dependency, subscription_dependency
from src.billing.schemas import PlanUpdate
from src.config import settings

stripe.api_key = settings.stripe_secret_key


class StripeGateway:
    @staticmethod
    async def save_plan_to_stripe(plan: Plan):
        try:
            if not plan.stripe_product_id:
                product = await run_in_threadpool(stripe.Product.create, name=plan.name)
                plan.stripe_product_id = product.id

            if not plan.stripe_price_id:
                price = await run_in_threadpool(stripe.Price.create,
                    unit_amount=plan.price_cents,   # in cents
                    currency=plan.currency,
                    recurring={"interval": "month"},
                    product=plan.stripe_product_id,
                )
                plan.stripe_price_id = price.id

            return plan
        
        except stripe.StripeError as e:
            # handle Stripe errors
            print(f"Stripe error: {e}")
            return None


    @staticmethod
    async def update_plan_in_stripe(plan: Plan, data: PlanUpdate) -> dict:
        update_data = data.model_dump(exclude_unset=True)

        product_update_data = {}
        if "name" in update_data:
            product_update_data["name"] = update_data["name"]

        if product_update_data:
            stripe.Product.update(plan.stripe_product_id, **product_update_data) #type: ignore

         # 2️⃣ If price-related fields changed → create new price
        if any(key in update_data for key in ["price_cents", "billing_period", "currency"]):
            new_price = stripe.Price.create(
                product=plan.stripe_product_id,
                unit_amount=update_data.get("price_cents", plan.price_cents),
                currency=update_data.get("currency", plan.currency),
                recurring={
                    "interval": update_data.get("billing_period", plan.billing_period)
                }
            )
            update_data["stripe_price_id"] = new_price.id

        return update_data

        
    @staticmethod
    async def soft_delete_plan_in_stripe(plan: Plan):
        stripe.Product.update(plan.stripe_product_id, active=False) #type: ignore
        stripe.Price.modify(plan.stripe_price_id, active=False)


    @staticmethod
    async def ensure_customer(user: User, user_repo: UserRepository) -> User:
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email)
            user = await user_repo.update(user, stripe_customer_id = customer['id'])
        
        return user


    @staticmethod
    async def create_subscription_checkout_session(user: User, plan: Plan,
        user_repo: UserRepository, old_stripe_sub_id: str | None = None ) -> str | None:

        await StripeGateway.ensure_customer(user, user_repo)
        metadata = {
            "plan_id": str(plan.id),
            "plan_code": plan.code,
            "plan_name": plan.name,
            "user_id": str(user.id),
        }
        if old_stripe_sub_id:
            metadata["upgrade_from_subscription_id"] = old_stripe_sub_id

        session = await run_in_threadpool(
            stripe.checkout.Session.create,
            mode="subscription",
            customer=user.stripe_customer_id,        
            line_items=[{
                "price": plan.stripe_price_id,
                "quantity": 1,
            }],
            success_url="https://yourapp.com/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://yourapp.com/cancel",
            client_reference_id=str(user.id),  
            subscription_data={"metadata": metadata},
        )

        return session.url


    @staticmethod
    async def user_subscripe(session, sub_repo: subscription_dependency, plan_repo: plan_dependency) -> Subscription:
        user_id = session.get("client_reference_id")
        new_stripe_sub_id = session.get("subscription")
        customer_id = session.get("customer")
        stripe_subscription = await run_in_threadpool(
            stripe.Subscription.retrieve,
            new_stripe_sub_id,
        )
        sub_metadata = stripe_subscription.get("metadata", {}) or {}
        old_stripe_sub_id = sub_metadata.get("upgrade_from_subscription_id")
        plan_id = sub_metadata.get("plan_id")
        if old_stripe_sub_id:
            await run_in_threadpool(
                stripe.Subscription.delete,
                old_stripe_sub_id,
            )
            await sub_repo.cancel_subscription(
                provider=PaymentProvider.STRIPE,
                provider_subscription_id=old_stripe_sub_id,
                canceled_at=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc),
            )
        plan = await plan_repo.get_by_id(plan_id) #type: ignore
        sub = await sub_repo.create_subscription(user_id, plan, PaymentProvider.STRIPE, new_stripe_sub_id, customer_id)
        return sub


    @staticmethod
    async def cancel_subscription_at_period_end(sub: Subscription) -> tuple[datetime, datetime | None]:
        stripe_subscription = None
        if sub.provider == PaymentProvider.STRIPE and sub.provider_subscription_id:
            stripe_subscription = await run_in_threadpool(
                    stripe.Subscription.modify,
                    sub.provider_subscription_id,
                    cancel_at_period_end=True,
                )
        
        now = datetime.now(timezone.utc)
        canceled_at = now
        current_period_end = sub.current_period_end
        
        if stripe_subscription is not None:
            canceled_at_ts = stripe_subscription.get("canceled_at")
            if canceled_at_ts:
                canceled_at = datetime.fromtimestamp(canceled_at_ts, tz=timezone.utc)

            cpe_ts = stripe_subscription.get("current_period_end")
            if cpe_ts:
                current_period_end = datetime.fromtimestamp(cpe_ts, tz=timezone.utc)

        #Current period end stay at the end of the month

        return canceled_at, current_period_end


    @staticmethod
    async def handle_invoice_payment_succeeded(invoice, sub_repo: subscription_dependency):
        lines = invoice.get("lines", {}).get("data", [])
        if not lines:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no lines in invoice")
        first_line = lines[0]
        parent = first_line.get("parent", {})
        sub_details = parent.get("subscription_item_details", {}) or {}
        stripe_subscription_id = sub_details.get("subscription")

        if not stripe_subscription_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No subscrition found.")
        
        stripe_subscription = await run_in_threadpool(
            stripe.Subscription.retrieve,
            stripe_subscription_id,
        )

        current_period_start = datetime.fromtimestamp(
            stripe_subscription["current_period_start"],
            tz=timezone.utc,
        )
        current_period_end = datetime.fromtimestamp(
            stripe_subscription["current_period_end"],
            tz=timezone.utc,
        )
        sub = await sub_repo.update_subscription_period(
            provider=PaymentProvider.STRIPE,
            provider_subscription_id=stripe_subscription_id,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
        )
        return sub
    

    @staticmethod
    async def handle_subscription_deleted(stripe_subscription, sub_repo: subscription_dependency):
        stripe_subscription_id = stripe_subscription.get("id")
        if not stripe_subscription_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer.subscription.deleted without id")
        
        canceled_at_ts = stripe_subscription.get("canceled_at")
        if canceled_at_ts:
            canceled_at = datetime.fromtimestamp(canceled_at_ts, tz=timezone.utc)
        else:
            canceled_at = datetime.now(timezone.utc)

        current_period_end_ts = stripe_subscription.get("current_period_end")
        current_period_end = None
        if current_period_end_ts:
            current_period_end = datetime.fromtimestamp(
                current_period_end_ts,
                tz=timezone.utc,
            )

         #Current period end changes to now so user has no access to the deleted plan

        sub = await sub_repo.cancel_subscription(
            provider=PaymentProvider.STRIPE,
            provider_subscription_id=stripe_subscription_id,
            canceled_at=canceled_at,
            current_period_end=current_period_end,
        )


        if not sub:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No local subscription found")

        return sub