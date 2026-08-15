"""ArbSubmission ORM model — an Architecture Review Board sign-off request and its decision.

The governance phase produces an ARB prep summary (architecture change + risk assessment); a human
**submits** it for review, an ARB approver **decides** (approve / reject / request-changes), and the
decision is recorded append-only in ``audit_log`` (see ``ArbService.decide``). This is the durable,
attributable ARB workflow the spec-driven spine's Governance phase gates on.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

ARB_STATUSES = ("pending", "approved", "rejected", "changes_requested")
# The decisions an approver may record, mapped to the resulting status.
ARB_DECISIONS = {
    "approve": "approved",
    "reject": "rejected",
    "request_changes": "changes_requested",
}


class ArbSubmission(Base, TimestampMixin):
    """One ARB review request: a prep summary, its status, and who submitted/decided it."""

    __tablename__ = "arb_submissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")  # architecture/risk prep
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")

    submitted_by: Mapped[str] = mapped_column(String(255), nullable=False)  # token subject
    submitter_persona: Mapped[str] = mapped_column(String(20), nullable=False)

    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewer_persona: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ArbSubmission id={self.id} status={self.status!r} title={self.title!r}>"
