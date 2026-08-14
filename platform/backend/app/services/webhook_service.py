"""WebhookEventService — inbound-delivery idempotency.

``record`` inserts a ``(source, delivery_id)`` row and reports whether the delivery is new. A duplicate
delivery (provider retry / at-least-once redelivery) returns ``False`` so the receiver can skip
re-dispatching side effects. Select-then-insert is deterministic under the single-writer test path;
production would rely on the unique constraint to catch a concurrent race.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.webhook_event import WebhookEvent

logger = get_logger(__name__)


class WebhookEventService:
    """Idempotency ledger for inbound webhook deliveries."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(self, source: str, delivery_id: str, event_type: str = "") -> bool:
        """Record a delivery; return True if new (proceed), False if already handled (skip)."""
        existing = await self._db.execute(
            select(WebhookEvent.id).where(
                WebhookEvent.source == source, WebhookEvent.delivery_id == delivery_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            logger.info("webhook.duplicate", source=source, delivery_id=delivery_id)
            return False
        self._db.add(
            WebhookEvent(source=source, delivery_id=delivery_id, event_type=event_type)
        )
        await self._db.flush()
        return True
