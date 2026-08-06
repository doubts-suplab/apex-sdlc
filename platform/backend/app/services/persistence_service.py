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

from app.agents.catalog import PHASE_CATALOG
from app.agents.orchestrator import JourneyResult
from app.agents.pricing import cost_usd
from app.core.logging import get_logger
from app.gates.engine import evaluate_journey
from app.models.agent_run import AgentRun
from app.models.artifact import Artifact, ArtifactVersion
from app.models.audit import AuditLog, PiiEvent, PolicyViolation
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
        n_audit = 0
        n_pii = 0
        n_violations = 0
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
                    input_tokens=jp.input_tokens,
                    output_tokens=jp.output_tokens,
                    cost_usd=jp.cost_usd,
                    duration_ms=jp.duration_ms,
                    model=jp.model,
                    provider=jp.provider,
                )
            )
            n_runs += 1

            # Golden rule #10 — one append-only audit entry per AI action.
            self._db.add(
                AuditLog(
                    project_id=project_id,
                    actor=jp.persona,
                    phase=jp.phase,
                    agent_name=jp.agent_name,
                    action=jp.action,
                    model=jp.model,
                    input_tokens=jp.input_tokens,
                    output_tokens=jp.output_tokens,
                    cost_usd=jp.cost_usd,
                    auto_enforced=jp.auto_enforced,
                    summary=f"{len(jp.artifacts)} artifact(s); {jp.rationale}"[:2000],
                )
            )
            n_audit += 1

            # PII events the guard recorded on this phase's agent I/O.
            for finding in jp.pii_findings:
                self._db.add(
                    PiiEvent(
                        project_id=project_id,
                        phase=jp.phase,
                        label=str(finding.get("label", "UNKNOWN")),
                        direction=str(finding.get("direction", "outgoing")),
                        action=str(finding.get("action", "redacted")),
                        occurrences=int(finding.get("occurrences", 1)),
                        confidence=float(finding.get("confidence", 1.0)),
                    )
                )
                n_pii += 1

            for art in jp.artifacts:
                n_artifacts += 1
                if await self._upsert_artifact(project_id, jp.phase, art):
                    n_versions += 1

            gate = gate_by_phase.get(jp.phase, {"status": "pending", "checks": []})

            # Policy violations: a governance-phase concern (ALERT/BLOCK) or a failing gate.
            n_violations += self._record_violations(project_id, jp, gate)
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
            "audit_entries": n_audit,
            "pii_events": n_pii,
            "policy_violations": n_violations,
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

    def _record_violations(
        self, project_id: uuid.UUID, jp: Any, gate: dict[str, Any]
    ) -> int:
        """Add PolicyViolation rows for a phase: a governance ALERT/BLOCK and/or a failing gate."""
        count = 0
        if jp.phase == "governance" and jp.action.lower() in ("alert", "block"):
            self._db.add(
                PolicyViolation(
                    project_id=project_id,
                    phase=jp.phase,
                    policy="ai-governance-review",
                    severity="critical" if jp.action.lower() == "block" else "high",
                    detail=jp.rationale[:2000],
                    status="open",
                    evidence={"action": jp.action, "confidence": jp.confidence},
                )
            )
            count += 1
        if gate.get("status") == "failed":
            self._db.add(
                PolicyViolation(
                    project_id=project_id,
                    phase=jp.phase,
                    policy="phase-gate",
                    severity="high",
                    detail=f"Phase gate failed for {jp.phase}.",
                    status="open",
                    evidence={"checks": gate.get("checks", [])},
                )
            )
            count += 1
        return count

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

    async def list_audit_log(self, project_id: uuid.UUID) -> list[AuditLog]:
        result = await self._db.execute(
            select(AuditLog).where(AuditLog.project_id == project_id).order_by(AuditLog.created_at)
        )
        return list(result.scalars().all())

    async def list_pii_events(self, project_id: uuid.UUID) -> list[PiiEvent]:
        result = await self._db.execute(
            select(PiiEvent).where(PiiEvent.project_id == project_id).order_by(PiiEvent.created_at)
        )
        return list(result.scalars().all())

    async def list_policy_violations(self, project_id: uuid.UUID) -> list[PolicyViolation]:
        result = await self._db.execute(
            select(PolicyViolation)
            .where(PolicyViolation.project_id == project_id)
            .order_by(PolicyViolation.created_at)
        )
        return list(result.scalars().all())

    async def cost_latency_by_persona(
        self, project_id: uuid.UUID, *, pricing_model: str | None = None
    ) -> dict[str, Any]:
        """Aggregate stored agent-run metering by owning persona (the per-persona cost dashboard).

        Each phase maps to its primary persona via the catalog; runs are grouped and summed. Explicit
        columns only (no ``SELECT *``); aggregation is in Python so the persona mapping stays in one place.
        ``pricing_model`` re-prices the stored token counts at that model (illustrative) instead of using
        each run's recorded ``cost_usd`` — useful when the runs were metered against a free/stub provider.
        """
        result = await self._db.execute(
            select(
                AgentRun.phase,
                AgentRun.input_tokens,
                AgentRun.output_tokens,
                AgentRun.cost_usd,
                AgentRun.duration_ms,
            ).where(AgentRun.project_id == project_id)
        )
        persona_for = {s.phase: s.primary_persona for s in PHASE_CATALOG}
        by_persona: dict[str, dict[str, Any]] = {}
        totals = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "runs": 0, "duration_ms": 0.0}
        for phase, in_tok, out_tok, stored_cost, duration in result.all():
            cost = cost_usd(pricing_model, in_tok, out_tok) if pricing_model else stored_cost
            persona = persona_for.get(phase, "unknown")
            bucket = by_persona.setdefault(
                persona,
                {"persona": persona, "runs": 0, "input_tokens": 0, "output_tokens": 0,
                 "cost_usd": 0.0, "duration_ms": 0.0},
            )
            bucket["runs"] += 1
            bucket["input_tokens"] += in_tok
            bucket["output_tokens"] += out_tok
            bucket["cost_usd"] += cost
            bucket["duration_ms"] += duration
            totals["runs"] += 1
            totals["input_tokens"] += in_tok
            totals["output_tokens"] += out_tok
            totals["cost_usd"] += cost
            totals["duration_ms"] += duration

        personas = []
        for bucket in sorted(by_persona.values(), key=lambda b: b["persona"]):
            runs = bucket["runs"] or 1
            bucket["cost_usd"] = round(bucket["cost_usd"], 6)
            bucket["avg_latency_ms"] = round(bucket["duration_ms"] / runs, 3)
            personas.append(bucket)
        totals["cost_usd"] = round(totals["cost_usd"], 6)
        return {"personas": personas, "totals": totals, "pricing_model": pricing_model or "actual"}
