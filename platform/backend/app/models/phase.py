from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

PHASE_STATUSES = ("pending", "active", "completed", "blocked")
GATE_STATUSES = ("pending", "passed", "failed")


class Phase(Base, TimestampMixin):
    """A lifecycle phase within a project."""

    __tablename__ = "phases"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project",
        back_populates="phases",
        lazy="noload",
    )
    gates: Mapped[list["PhaseGate"]] = relationship(
        "PhaseGate",
        back_populates="phase",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Phase id={self.id} type={self.phase_type!r} status={self.status!r}>"


class PhaseGate(Base):
    """A quality gate within a phase."""

    __tablename__ = "phase_gates"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    phase_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("phases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    criteria: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evaluated_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    phase: Mapped["Phase"] = relationship(
        "Phase",
        back_populates="gates",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<PhaseGate id={self.id} type={self.gate_type!r} status={self.status!r}>"
