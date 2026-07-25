"""
Celery worker configuration for Kunj.
"""
from celery import Celery
from config import settings

app = Celery(
    "kunj",
    broker=settings.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=settings.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=["tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
