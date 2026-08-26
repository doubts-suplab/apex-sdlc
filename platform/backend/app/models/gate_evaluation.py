"""Persisted phase-gate evaluations — a durable, append-only record of gate decisions.

The phase-gate engine (:mod:`app.gates.engine`) is pure: it evaluates a phase's gate from explicit
inputs and returns a :class:`~app.gates.engine.GateResult`. Persisting each evaluation makes the
spec-driven spine *auditable over time* — who evaluated which phase, what the outcome was, and which
checks passed — rather than only reflecting the live gate status. Each evaluation is a new row (never
mutated): the history of a phase's gate is the ordered sequence of its evaluations.
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AppendOnly, Base, TimestampMixin

# JSONB on PostgreSQL (production); generic JSON elsewhere (SQLite in tests) so the schema compiles.
_JSON = JSON().with_variant(JSONB, "postgresql")

GATE_STATUSES = ("passed", "pending", "failed")


class GateEvaluation(Base, TimestampMixin, AppendOnly):
    """One persisted evaluation of a phase gate. Append-only (governance invariant)."""

    __tablename__ = "gate_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # passed | pending | failed
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    bypass_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluated_by: Mapped[str] = mapped_column(String(100), nullable=False, default="")  # persona/subject
    checks: Mapped[list[dict[str, object]]] = mapped_column(_JSON, nullable=False, default=list)

    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<GateEvaluation id={self.id} phase={self.phase!r} status={self.status!r}>"
