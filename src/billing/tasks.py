import asyncio
from celery import shared_task
from src.celery_app import celery_app, beat_app
from datetime import datetime, timezone
from asgiref.sync import async_to_sync
from sqlalchemy import update
from src import load_models
from src.billing.emails import Emails
from src.billing.models import Subscription, SubscriptionStatus

from src.database import get_sync_session


email_service = Emails()

@celery_app.task(name="send_subscription_email_task")
def send_subscription_email_task(subscription: dict):
    async_to_sync(email_service.send_subscription_email)(subscription)


@beat_app.task(name="expire_subscriptions_task")
def expire_subscriptions_task():
    db = get_sync_session()

    now = datetime.now(timezone.utc)


    db.execute(
        update(Subscription)
        .where(Subscription.current_period_end <= now)
        .where(Subscription.status != SubscriptionStatus.EXPIRED)
        .values(status=SubscriptionStatus.EXPIRED)
    )

    db.commit()
    db.close()

