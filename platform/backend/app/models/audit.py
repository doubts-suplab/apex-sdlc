"""Governance ORM models — the append-only audit trail and its governance siblings.

- ``AuditLog`` — one append-only record per AI action (golden rule #10): actor, model, phase, action,
  token/cost accounting, and a before/after summary. Never updated or deleted.
- ``PiiEvent`` — a PII-guard detection on agent I/O: the label, where it was seen, and the action taken.
- ``PolicyViolation`` — a governance/policy concern raised during a run (e.g. a governance-phase ALERT or
  a failing gate), with severity and remediation status for the CISO view.
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

# JSONB on PostgreSQL (production); generic JSON elsewhere (SQLite in tests) so the schema compiles.
_JSON = JSON().with_variant(JSONB, "postgresql")

PII_ACTIONS = ("redacted", "logged", "blocked")
VIOLATION_SEVERITIES = ("low", "medium", "high", "critical")
REMEDIATION_STATUSES = ("open", "acknowledged", "resolved", "waived")


class AuditLog(Base, TimestampMixin):
    """Append-only record of one AI action. Never mutated (governance invariant)."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor: Mapped[str] = mapped_column(String(100), nullable=False)  # persona / user id
    phase: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # the decision action
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    auto_enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")  # human-readable after-state

    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} phase={self.phase!r} action={self.action!r}>"


class PiiEvent(Base, TimestampMixin):
    """A PII-guard detection on agent I/O."""

    __tablename__ = "pii_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False)  # EMAIL | SSN | CREDIT_CARD | …
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # "outgoing" | "incoming"
    action: Mapped[str] = mapped_column(String(20), nullable=False, default="redacted")
    occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<PiiEvent id={self.id} label={self.label!r} phase={self.phase!r}>"


class PolicyViolation(Base, TimestampMixin):
    """A governance/policy concern raised during a run, tracked for the CISO view."""

    __tablename__ = "policy_violations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    policy: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    evidence: Mapped[dict[str, object]] = mapped_column(_JSON, nullable=False, default=dict)

    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<PolicyViolation id={self.id} policy={self.policy!r} severity={self.severity!r}>"
