from __future__ import annotations

import os

from celery import Celery

from app.core.logging import get_logger

logger = get_logger(__name__)

# Read connection URLs from environment (or fall back to defaults for local dev)
_redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "apex_platform",
    broker=_redis_url,
    backend=_redis_url,
    include=[],  # task modules will be added here as Phase 2+ work progresses
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Beat schedule placeholder — tasks will be registered in future phases
    beat_schedule={},
)

logger.info("celery.configured", broker=_redis_url)
