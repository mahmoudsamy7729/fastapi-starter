import stripe
import json
from fastapi.concurrency import run_in_threadpool
from uuid import UUID
from src.rate_limiter import limiter
from fastapi import APIRouter, status, Request, Header
from src.billing.service import PlanService, SubscriptionService
from src.billing import schemas
from src.billing.dependencies import plan_dependency, subscription_dependency
from src.auth.dependencies import repo_dependency
from src.auth_bearer import  user_dependency, admin_user_dependency
from src.billing.tasks import send_subscription_email_task
from src.billing.utils import serialize_subscription
from src.config import settings



router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[schemas.PlanOut], status_code=status.HTTP_200_OK)
async def list_plans(plan_dep: plan_dependency):
    result = await PlanService.retrive_plans(plan_dep)
    return result


@router.post("/plans", response_model=schemas.PlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(data: schemas.PlanCreate, plan_dep: plan_dependency, admin_user: admin_user_dependency):
    result = await PlanService.create_plan(data, plan_dep)
    if result:
        return result


@router.get("/plans/{plan_id}", response_model=schemas.PlanOut, status_code=status.HTTP_200_OK)
async def get_plan(plan_id: UUID, plan_dep: plan_dependency):
    plan = await PlanService.get_plan_by_id(plan_id, plan_dep)
    return plan


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: UUID, plan_deb: plan_dependency, admin_user: admin_user_dependency):
    result = await PlanService.soft_delete_plan(plan_id, plan_deb)


@router.patch("/plans/{plan_id}", response_model=schemas.PlanOut, status_code=status.HTTP_200_OK)
async def update_plan(plan_id: UUID, data: schemas.PlanUpdate, plan_dep: plan_dependency, admin_user: admin_user_dependency):
    return await PlanService.update_plan(plan_id, data, plan_dep)


@router.get("/subscriptions/me", response_model=schemas.SubscriptionOut, status_code=status.HTTP_200_OK)
async def get_my_subscription(user: user_dependency, sub_dep: subscription_dependency):
    subscription = await SubscriptionService.get_user_subscription(user.id, sub_dep)
    return subscription


@router.post("/subscriptions/subscribe", response_model=schemas.CheckoutUrlResponse, status_code=status.HTTP_201_CREATED)
async def subscribe_to_plan(user: user_dependency, data: schemas.SubscribeRequest,
                sub_dep: subscription_dependency, plan_dep: plan_dependency, user_repo: repo_dependency):
    checkout_url = await SubscriptionService.subscribe_user_to_plan(user, data.plan_code, sub_dep, plan_dep, user_repo)
    return checkout_url


@router.post("/subscriptions/cancel", response_model=schemas.SubscriptionOut, status_code=status.HTTP_200_OK)
async def cancel_subscription_at_end_of_period(user: user_dependency, sub_deb: subscription_dependency):
    subscription = await SubscriptionService.cancel_subscription_at_end_of_period(user.id, sub_deb)
    return subscription


@router.post("/subscriptions/upgrade", response_model=schemas.CheckoutUrlResponse, status_code=status.HTTP_200_OK)
async def upgrade_subscription(data: schemas.SubscribeRequest, user: user_dependency, sub_repo: subscription_dependency,
    plan_repo: plan_dependency, user_repo: repo_dependency):
    sub = await SubscriptionService.upgrade_subscription(user, data.plan_code, sub_repo, plan_repo, user_repo)
    return sub


@router.post("/stripe/webhook")
@limiter.exempt
async def stripe_webhook(request: Request, sub_dep: subscription_dependency, plan_dep: plan_dependency,
        stripe_signature: str = Header(str)):
    await SubscriptionService.stripe_webhook(request, stripe_signature, sub_dep, plan_dep)
    return {"message": "Unhandled event"}





    
