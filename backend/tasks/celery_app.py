"""
Celery App – configuration for distributed task execution.
Uses Redis as both broker and result backend.
"""

from celery import Celery
from config.settings import settings

celery_app = Celery(
    "ai_knowledge_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
)

# In the future, we'll register tasks here via:
# celery_app.autodiscover_tasks(['backend.tasks'])
