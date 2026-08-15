"""ArbService — the Architecture Review Board sign-off workflow.

``submit`` records a pending ARB request; ``decide`` sets its outcome and writes an **append-only**
``AuditLog`` row (the decision is attributable and immutable, like every governed action). Follows
the async-service pattern used across the platform.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.arb import ARB_DECISIONS, ArbSubmission
from app.models.audit import AuditLog

logger = get_logger(__name__)


class ArbService:
    """Submit, read, and decide Architecture Review Board requests."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def submit(
        self,
        project_id: uuid.UUID,
        *,
        title: str,
        summary: str,
        submitted_by: str,
        submitter_persona: str,
    ) -> ArbSubmission:
        """Record a pending ARB review request."""
        arb = ArbSubmission(
            project_id=project_id,
            title=title,
            summary=summary,
            status="pending",
            submitted_by=submitted_by,
            submitter_persona=submitter_persona,
        )
        self._db.add(arb)
        await self._db.flush()
        await self._db.refresh(arb)
        logger.info("arb.submitted", id=str(arb.id), project_id=str(project_id), by=submitted_by)
        return arb

    async def list(self, project_id: uuid.UUID) -> list[ArbSubmission]:
        result = await self._db.execute(
            select(ArbSubmission)
            .where(ArbSubmission.project_id == project_id)
            .order_by(ArbSubmission.created_at)
        )
        return list(result.scalars().all())

    async def get(self, project_id: uuid.UUID, arb_id: uuid.UUID) -> ArbSubmission | None:
        result = await self._db.execute(
            select(ArbSubmission).where(
                ArbSubmission.id == arb_id, ArbSubmission.project_id == project_id
            )
        )
        return result.scalar_one_or_none()

    async def decide(
        self,
        arb: ArbSubmission,
        *,
        decision: str,
        reviewer: str,
        reviewer_persona: str,
        rationale: str,
    ) -> ArbSubmission:
        """Apply an ARB decision to a submission and record it append-only in the audit log.

        ``decision`` is one of ``approve`` / ``reject`` / ``request_changes`` (mapped to the
        resulting status). Recording an audit row is part of the same unit of work — an ARB
        decision without an audit trail would be a governance gap.
        """
        arb.status = ARB_DECISIONS[decision]
        arb.reviewed_by = reviewer
        arb.reviewer_persona = reviewer_persona
        arb.decision_rationale = rationale
        arb.decided_at = datetime.now(UTC)
        self._db.add(
            AuditLog(
                project_id=arb.project_id,
                actor=reviewer,
                phase="governance",
                agent_name="arb",
                action=f"arb-{arb.status}"[:20],
                summary=f"ARB {arb.status} — {arb.title}: {rationale}"[:2000],
            )
        )
        await self._db.flush()
        await self._db.refresh(arb)
        logger.info(
            "arb.decided",
            id=str(arb.id),
            status=arb.status,
            reviewer=reviewer,
            project_id=str(arb.project_id),
        )
        return arb
