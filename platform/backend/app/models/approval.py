"""GateApproval ORM model — a durable, identity-bound human approval of a phase spec.

APEX's spine gates a phase transition on human approval of that phase's spec (artifact). Until now an
approval was ephemeral — a ``?approved=<phase>`` query param evaluated in-memory and never recorded.
``GateApproval`` makes it **durable and attributable**: who approved (JWT subject + persona), when, bound
to the project ``Member`` when one exists, as an append-only history. "Currently approved" for a phase is
the latest approval whose ``decision`` is ``approved`` (a later ``rejected`` withdraws it).
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

APPROVAL_DECISIONS = ("approved", "rejected")


class GateApproval(Base, TimestampMixin):
    """One human decision on a phase's spec — append-only; latest decision per phase wins."""

    __tablename__ = "gate_approvals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase: Mapped[str] = mapped_column(String(50), nullable=False)  # one of models.project.PHASE_TYPES
    # Identity of the approver, straight from the bearer token.
    approver_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_persona: Mapped[str] = mapped_column(String(20), nullable=False)
    # Bound to the project Member when the subject maps to one (SET NULL if the member is later removed).
    member_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("members.id", ondelete="SET NULL"), nullable=True, index=True
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False, default="approved")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Project", lazy="noload"
    )
    member: Mapped["Member | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Member", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<GateApproval project={self.project_id} phase={self.phase!r} "
            f"decision={self.decision!r} by={self.approver_subject!r}>"
        )
