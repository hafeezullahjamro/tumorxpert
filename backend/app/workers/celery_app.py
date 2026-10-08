from __future__ import annotations

from celery import Celery

from ..core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tumorxpert",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


@celery_app.task(name="tumorxpert.run_mock_inference")
def run_mock_inference_task(study_id: str) -> str:
    # TODO: integrate real model inference pipeline.
    return f"Mock inference queued for study {study_id}"
