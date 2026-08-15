from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

DELIVERY_STATUSES = ("proposed", "planned", "in_progress", "done", "dropped")
DELIVERY_PRIORITIES = ("low", "medium", "high", "critical")
DELIVERY_SOURCES = ("human", "agent")


class Delivery(Base, TimestampMixin):
    """A planned unit of work for a project — the atom of delivery planning.

    A delivery is a proposed/planned piece of work (an epic-sized item) belonging to one project.
    The PlanningAgent proposes deliveries at ``source='agent', status='proposed'`` for a human to
    accept; a human can also author them directly. This is the read/write model an operator uses to
    plan a project's next deliveries — distinct from ``artifacts`` (generated documents) and
    ``phases`` (the SDLC spine).
    """

    __tablename__ = "deliveries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # proposed → planned → in_progress → done (or dropped)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="proposed")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    # Estimate in points (nullable — a freshly proposed delivery may be unsized).
    estimate_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # A free-form target reference (milestone / version / iteration).
    target_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Who created it: a human operator or the planning agent.
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="human")

    def __repr__(self) -> str:
        return f"<Delivery id={self.id} project={self.project_id} title={self.title!r}>"
