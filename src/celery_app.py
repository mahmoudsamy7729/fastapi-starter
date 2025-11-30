from celery import Celery
from celery.schedules import crontab
from src.config import settings


celery_app = Celery(
    "worker",
    broker=settings.celery_worker_url,
    backend=None,
    include=["src.tasks", "src.billing.tasks"]
)


beat_app = Celery(
    "beat_worker",
    broker=settings.celery_beat_url,
    backend=None,
    include=["src.billing.tasks"]
)

celery_app.conf.task_routes = {
    "src.tasks.*": {"queue": "default"},
    "src.billing.tasks.*": {"queue": "billing"},
}


beat_app.conf.beat_schedule = {
    "expire-subscriptions-every-hour": {
        "task": "expire_subscriptions_task",
        "schedule": crontab(minute=0, hour="*"),  
    },
}
