from .celery_app import celery_app
from datetime import datetime

@celery_app.task
def expire_subscriptions():
    print(f"Checking for expired subscriptions at {datetime.utcnow()}")
    # TODO: fetch subscriptions from DB and mark expired
