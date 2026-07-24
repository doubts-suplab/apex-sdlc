"""PersistenceService — store a governed journey run (agent runs, artifacts, phase gates) and read it back.

Turns the previously ephemeral outputs into queryable state. Pure DB access (AsyncSession); the harness /
gate engine remain framework-free. Mirrors the ``ProjectService`` pattern.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import JourneyResult
from app.core.logging import get_logger
from app.gates.engine import evaluate_journey
from app.models.agent_run import AgentRun
from app.models.artifact import Artifact, ArtifactVersion
from app.models.phase import Phase, PhaseGate

logger = get_logger(__name__)

# Gate status (passed | pending | failed) → project phase status.
_PHASE_STATUS = {"passed": "completed", "pending": "active", "failed": "blocked"}


class PersistenceService:
    """Persist and read a project's governed journey outputs."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def persist_journey(
        self,
        project_id: uuid.UUID,
        journey: JourneyResult,
        approvals: set[str] | None = None,
    ) -> dict[str, Any]:
        """Persist every phase's agent run, artifacts, and gate; return a summary."""
        approvals = approvals or set()
        gate_eval = evaluate_journey(journey, approvals)
        gate_by_phase = {g["phase"]: g for g in gate_eval["gates"]}

        n_runs = 0
        n_artifacts = 0
        n_versions = 0
        for jp in journey.phases:
            self._db.add(
                AgentRun(
                    project_id=project_id,
                    phase=jp.phase,
                    agent_name=jp.agent_name,
                    action=jp.action,
                    confidence=jp.confidence,
                    auto_enforced=jp.auto_enforced,
                    outcome=jp.outcome,
                    rationale=jp.rationale,
                    status="completed",
                )
            )
            n_runs += 1
            for art in jp.artifacts:
                n_artifacts += 1
                if await self._upsert_artifact(project_id, jp.phase, art):
                    n_versions += 1

            gate = gate_by_phase.get(jp.phase, {"status": "pending", "checks": []})
            phase = Phase(
                project_id=project_id,
                phase_type=jp.phase,
                status=_PHASE_STATUS.get(gate["status"], "active"),
            )
            self._db.add(phase)
            await self._db.flush()  # need phase.id for the gate FK
            self._db.add(
                PhaseGate(
                    phase_id=phase.id,
                    gate_type="spec-gate",
                    criteria={"checks": gate.get("checks", [])},
                    status=gate["status"],
                    created_at=datetime.now(UTC),
                )
            )

        await self._db.flush()
        logger.info(
            "journey.persisted",
            project_id=str(project_id),
            agent_runs=n_runs,
            artifacts=n_artifacts,
            blocking_phase=gate_eval["blocking_phase"],
        )
        return {
            "project_id": str(project_id),
            "agent_runs": n_runs,
            "artifacts": n_artifacts,
            "new_versions": n_versions,
            "phases": len(journey.phases),
            "blocking_phase": gate_eval["blocking_phase"],
            "all_passed": gate_eval["all_passed"],
        }

    async def _upsert_artifact(self, project_id: uuid.UUID, phase: str, art: dict[str, Any]) -> bool:
        """Upsert one artifact by (project, phase, name); snapshot a new version on content change.

        Returns True if a new version was written (first insert or changed content), False if the content
        was unchanged (idempotent re-persist).
        """
        content = str(art["content"])
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        existing = (
            await self._db.execute(
                select(Artifact).where(
                    Artifact.project_id == project_id,
                    Artifact.phase == phase,
                    Artifact.name == art["name"],
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            artifact = Artifact(
                project_id=project_id,
                phase=phase,
                name=art["name"],
                title=art.get("title", ""),
                kind=art.get("kind", "md"),
                content=content,
                content_sha256=sha,
                version=1,
            )
            self._db.add(artifact)
            await self._db.flush()  # need artifact.id for the version FK
            self._db.add(
                ArtifactVersion(artifact_id=artifact.id, version=1, content=content, content_sha256=sha)
            )
            return True

        if existing.content_sha256 == sha:
            return False  # unchanged — idempotent

        existing.version += 1
        existing.content = content
        existing.content_sha256 = sha
        existing.title = art.get("title", existing.title)
        self._db.add(
            ArtifactVersion(
                artifact_id=existing.id, version=existing.version, content=content, content_sha256=sha
            )
        )
        return True

    async def list_artifact_versions(self, artifact_id: uuid.UUID) -> list[ArtifactVersion]:
        result = await self._db.execute(
            select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact_id)
            .order_by(ArtifactVersion.version)
        )
        return list(result.scalars().all())

    async def list_artifacts(self, project_id: uuid.UUID) -> list[Artifact]:
        result = await self._db.execute(
            select(Artifact)
            .where(Artifact.project_id == project_id)
            .order_by(Artifact.phase, Artifact.name)
        )
        return list(result.scalars().all())

    async def list_agent_runs(self, project_id: uuid.UUID) -> list[AgentRun]:
        result = await self._db.execute(
            select(AgentRun)
            .where(AgentRun.project_id == project_id)
            .order_by(AgentRun.created_at)
        )
        return list(result.scalars().all())

    async def gate_matrix(self, project_id: uuid.UUID) -> list[dict[str, str]]:
        result = await self._db.execute(
            select(Phase.phase_type, PhaseGate.status)
            .join(PhaseGate, PhaseGate.phase_id == Phase.id)
            .where(Phase.project_id == project_id)
        )
        return [{"phase": phase_type, "status": status} for phase_type, status in result.all()]
