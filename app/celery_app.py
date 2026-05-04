from celery import Celery
from app.core.config import setting

celery_app = Celery(
    "worker",
    broker=setting.REDIS_URL,
    backend=setting.REDIS_URL,
    include=["app.tasks.meeting_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
)
