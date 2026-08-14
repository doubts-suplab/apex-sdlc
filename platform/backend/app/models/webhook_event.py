"""WebhookEvent ORM model — inbound-delivery de-dup ledger for idempotency.

Providers re-deliver webhooks (retries, at-least-once delivery), so acting on every POST would
double-dispatch. Each delivery carries a stable id — GitHub's ``X-GitHub-Delivery`` header, or a content
hash for providers (Jira) that don't send one. Recording ``(source, delivery_id)`` with a uniqueness
constraint lets the receiver skip a delivery it has already handled.
"""

from __future__ import annotations

import uuid

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WebhookEvent(Base, TimestampMixin):
    """One handled inbound webhook delivery — the idempotency key is ``(source, delivery_id)``."""

    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("source", "delivery_id", name="uq_webhook_source_delivery"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # "github" | "jira"
    delivery_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    def __repr__(self) -> str:
        return f"<WebhookEvent source={self.source!r} delivery={self.delivery_id!r}>"
