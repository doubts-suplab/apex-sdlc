"""Persistence API — persist a project's governed journey and read the stored state back.

``POST /projects/{id}/journey/persist`` runs the reference journey for a project and stores its agent
runs, artifacts, and phase gates; the ``GET`` endpoints read them. Requires a database (production path).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.agents.catalog import PHASE_ORDER
from app.agents.orchestrator import run_reference_journey, run_single_phase
from app.gates.engine import evaluate_gate
from app.api.deps import require_project_member
from app.core.security import Principal, require_persona
from app.db.session import DbSession
from app.integrations.llm.factory import get_llm_provider
from app.models.project import Project
from app.services.persistence_service import PersistenceService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["persistence"])

# Personas allowed to run + approve a journey (a spec-approval / gate action). Read endpoints stay
# open for now; global auth enforcement on every route is the follow-on (see docs/progress.md).
_APPROVER_PERSONAS = ("lead", "ba", "architect", "ciso")
# Governance data (audit log, PII events, policy violations) is CISO/Lead-only (platform CLAUDE.md).
_GOVERNANCE_PERSONAS = ("ciso", "lead")


def _svc(db: DbSession) -> PersistenceService:
    return PersistenceService(db)


Svc = Annotated[PersistenceService, Depends(_svc)]


async def _load_project(db: DbSession, project_id: uuid.UUID) -> Project:
    project = await ProjectService(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/project-not-found",
                "title": "Project Not Found",
                "status": 404,
                "detail": f"No project with id={project_id} exists.",
            },
        )
    return project


async def _require_project(db: DbSession, project_id: uuid.UUID) -> None:
    await _load_project(db, project_id)


def _require_known_phase(phase: str) -> None:
    if phase not in PHASE_ORDER:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/unknown-phase",
                "title": "Unknown Phase",
                "status": 404,
                "detail": f"Phase {phase!r} is not one of {list(PHASE_ORDER)}.",
            },
        )


class ApprovalRequest(BaseModel):
    """Body for approving/rejecting a phase spec."""

    decision: str = Field(default="approved", pattern="^(approved|rejected)$")
    note: str | None = Field(default=None, max_length=2000)


def _project_dict(project: Project, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the agent-facing project dict from the stored project, enriched with per-run inputs."""
    base: dict[str, Any] = {
        "name": project.name,
        "slug": project.slug,
        "description": project.description or "",
        "github_repo": project.github_repo or "",
    }
    base.update(inputs or {})
    return base


@router.post("/{project_id}/journey/persist", summary="Run + persist the reference journey for a project")
async def persist_journey(
    project_id: uuid.UUID,
    db: DbSession,
    svc: Svc,
    principal: Annotated[Principal, Depends(require_persona(*_APPROVER_PERSONAS))],
    approved: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    await _require_project(db, project_id)
    # Durable approvals recorded via POST .../approve are authoritative; the ad-hoc ?approved= query
    # param still works and is unioned on top (handy for one-off runs / demos).
    approvals = await svc.approved_phases(project_id)
    if approved:
        approvals |= {p.strip() for p in approved.split(",")}
    journey = run_reference_journey(get_llm_provider())
    return await svc.persist_journey(project_id, journey, approvals)


@router.post(
    "/{project_id}/phases/{phase}/approve",
    summary="Record a durable, identity-bound approval of a phase spec",
)
async def approve_phase(
    project_id: uuid.UUID,
    phase: str,
    db: DbSession,
    svc: Svc,
    principal: Annotated[Principal, Depends(require_persona(*_APPROVER_PERSONAS))],
    _member: Annotated[Principal, Depends(require_project_member)],
    body: ApprovalRequest | None = None,
) -> dict[str, Any]:
    """Approve/reject a phase's spec as the authenticated approver; persisted + attributable."""
    _require_known_phase(phase)
    await _require_project(db, project_id)
    req = body or ApprovalRequest()
    approval = await svc.record_approval(
        project_id,
        phase,
        approver_subject=principal.subject,
        approver_persona=principal.persona,
        decision=req.decision,
        note=req.note,
    )
    return {
        "id": str(approval.id),
        "project_id": str(approval.project_id),
        "phase": approval.phase,
        "decision": approval.decision,
        "approver_subject": approval.approver_subject,
        "approver_persona": approval.approver_persona,
        "member_bound": approval.member_id is not None,
        "note": approval.note,
    }


@router.get("/{project_id}/approvals", summary="Stored gate approvals for a project (history)")
async def list_approvals(project_id: uuid.UUID, db: DbSession, svc: Svc) -> dict[str, Any]:
    await _require_project(db, project_id)
    items = await svc.list_approvals(project_id)
    current = await svc.approved_phases(project_id)
    return {
        "total": len(items),
        "approved_phases": sorted(current),
        "items": [
            {
                "id": str(a.id),
                "phase": a.phase,
                "decision": a.decision,
                "approver_subject": a.approver_subject,
                "approver_persona": a.approver_persona,
                "member_bound": a.member_id is not None,
                "note": a.note,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ],
    }


@router.post(
    "/{project_id}/phases/{phase}/agents/run-persist",
    summary="Run one phase agent for a project and persist the run",
)
async def run_and_persist_phase(
    project_id: uuid.UUID,
    phase: str,
    db: DbSession,
    svc: Svc,
    principal: Annotated[Principal, Depends(require_persona(*_APPROVER_PERSONAS))],
) -> dict[str, Any]:
    """Execution + persistence primitive behind an event-driven trigger (webhook → phase run)."""
    if phase not in PHASE_ORDER:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/unknown-phase",
                "title": "Unknown Phase",
                "status": 404,
                "detail": f"Phase {phase!r} is not one of {list(PHASE_ORDER)}.",
            },
        )
    project = await _load_project(db, project_id)
    jp = run_single_phase(_project_dict(project), phase, get_llm_provider())
    return await svc.persist_phase(project_id, jp)


@router.get("/{project_id}/artifacts", summary="Stored artifacts for a project")
async def list_artifacts(project_id: uuid.UUID, db: DbSession, svc: Svc) -> dict[str, Any]:
    await _require_project(db, project_id)
    items = await svc.list_artifacts(project_id)
    return {
        "total": len(items),
        "items": [
            {
                "id": str(a.id),
                "phase": a.phase,
                "name": a.name,
                "kind": a.kind,
                "version": a.version,
                "content_sha256": a.content_sha256,
            }
            for a in items
        ],
    }


@router.get("/{project_id}/artifacts/{artifact_id}", summary="A stored artifact with its content")
async def get_artifact(
    project_id: uuid.UUID, artifact_id: uuid.UUID, db: DbSession, svc: Svc
) -> dict[str, Any]:
    await _require_project(db, project_id)
    art = await svc.get_artifact(project_id, artifact_id)
    if art is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/artifact-not-found",
                "title": "Artifact Not Found",
                "status": 404,
                "detail": f"No artifact {artifact_id} in project {project_id}.",
            },
        )
    return {
        "id": str(art.id),
        "phase": art.phase,
        "name": art.name,
        "title": art.title,
        "kind": art.kind,
        "version": art.version,
        "content_sha256": art.content_sha256,
        "content": art.content,
    }


@router.get(
    "/{project_id}/artifacts/{artifact_id}/versions",
    summary="Version lineage for a stored artifact",
)
async def list_versions(
    project_id: uuid.UUID, artifact_id: uuid.UUID, db: DbSession, svc: Svc
) -> dict[str, Any]:
    await _require_project(db, project_id)
    versions = await svc.list_artifact_versions(artifact_id)
    return {
        "total": len(versions),
        "items": [
            {"version": v.version, "content_sha256": v.content_sha256} for v in versions
        ],
    }


@router.get("/{project_id}/agent-runs", summary="Stored agent runs for a project")
async def list_agent_runs(project_id: uuid.UUID, db: DbSession, svc: Svc) -> dict[str, Any]:
    await _require_project(db, project_id)
    items = await svc.list_agent_runs(project_id)
    return {
        "total": len(items),
        "items": [
            {
                "id": str(r.id),
                "phase": r.phase,
                "agent_name": r.agent_name,
                "action": r.action,
                "confidence": r.confidence,
                "auto_enforced": r.auto_enforced,
                "outcome": r.outcome,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_usd": r.cost_usd,
                "duration_ms": r.duration_ms,
                "model": r.model,
            }
            for r in items
        ],
    }


@router.get("/{project_id}/gate-status", summary="Stored phase-gate statuses for a project")
async def gate_status(project_id: uuid.UUID, db: DbSession, svc: Svc) -> dict[str, Any]:
    await _require_project(db, project_id)
    return {"gates": await svc.gate_matrix(project_id)}


class GateEvaluationInput(BaseModel):
    """Inputs to evaluate (and persist) a phase's gate."""

    produced_artifacts: list[str] = Field(default_factory=list)
    auto_enforced: bool = False
    approved: bool = False
    bypass_total: int = 0


@router.post(
    "/{project_id}/phases/{phase}/gate/evaluations",
    status_code=201,
    summary="Evaluate a phase gate and persist the result (append-only)",
)
async def persist_gate_evaluation(
    project_id: uuid.UUID,
    phase: str,
    body: GateEvaluationInput,
    db: DbSession,
    svc: Svc,
    principal: Annotated[Principal, Depends(require_persona(*_APPROVER_PERSONAS))],
) -> dict[str, Any]:
    """Evaluate a phase gate through the pure engine and store the evaluation as a durable,
    append-only record (who evaluated it, the outcome, and which checks passed)."""
    await _require_project(db, project_id)
    if phase not in PHASE_ORDER:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/unknown-phase",
                "title": "Unknown phase",
                "status": 404,
                "detail": f"Phase {phase!r} is not one of {list(PHASE_ORDER)}.",
            },
        )
    result = evaluate_gate(
        phase,
        produced_artifacts=body.produced_artifacts,
        auto_enforced=body.auto_enforced,
        approved=body.approved,
        bypass_total=body.bypass_total,
    )
    saved = await svc.save_gate_evaluation(
        project_id, result, evaluated_by=principal.subject, bypass_total=body.bypass_total
    )
    return {
        "id": str(saved.id),
        "project_id": str(project_id),
        "phase": saved.phase,
        "status": saved.status,
        "reason": saved.reason,
        "bypass_total": saved.bypass_total,
        "evaluated_by": saved.evaluated_by,
        "checks": saved.checks,
        "evaluated_at": saved.created_at.isoformat() if saved.created_at else None,
    }


@router.get(
    "/{project_id}/gate/evaluations",
    summary="Persisted phase-gate evaluation history for a project",
)
async def list_gate_evaluations(
    project_id: uuid.UUID,
    db: DbSession,
    svc: Svc,
    phase: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    await _require_project(db, project_id)
    evaluations = await svc.list_gate_evaluations(project_id, phase)
    return {
        "project_id": str(project_id),
        "total": len(evaluations),
        "items": [
            {
                "id": str(e.id),
                "phase": e.phase,
                "status": e.status,
                "reason": e.reason,
                "bypass_total": e.bypass_total,
                "evaluated_by": e.evaluated_by,
                "checks": e.checks,
                "evaluated_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in evaluations
        ],
    }


@router.get(
    "/{project_id}/metrics/cost-latency",
    summary="Cost / token / latency dashboard, aggregated per persona",
)
async def cost_latency(
    project_id: uuid.UUID,
    db: DbSession,
    svc: Svc,
    model: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Per-persona metering for a persisted project. ``model`` re-prices the stored token counts
    illustratively (useful when runs were metered against a free/stub provider)."""
    await _require_project(db, project_id)
    return await svc.cost_latency_by_persona(project_id, pricing_model=model)


# -- governance (CISO/Lead only) ----------------------------------------------------------------
GovPrincipal = Annotated[Principal, Depends(require_persona(*_GOVERNANCE_PERSONAS))]


@router.get("/{project_id}/governance/audit-log", summary="Append-only AI-action audit log (CISO/Lead)")
async def audit_log(project_id: uuid.UUID, db: DbSession, svc: Svc, _p: GovPrincipal) -> dict[str, Any]:
    await _require_project(db, project_id)
    items = await svc.list_audit_log(project_id)
    return {
        "total": len(items),
        "items": [
            {
                "id": str(a.id),
                "actor": a.actor,
                "phase": a.phase,
                "agent_name": a.agent_name,
                "action": a.action,
                "model": a.model,
                "input_tokens": a.input_tokens,
                "output_tokens": a.output_tokens,
                "cost_usd": a.cost_usd,
                "auto_enforced": a.auto_enforced,
                "summary": a.summary,
            }
            for a in items
        ],
    }


@router.get("/{project_id}/governance/pii-events", summary="PII-guard detections on agent I/O (CISO/Lead)")
async def pii_events(project_id: uuid.UUID, db: DbSession, svc: Svc, _p: GovPrincipal) -> dict[str, Any]:
    await _require_project(db, project_id)
    items = await svc.list_pii_events(project_id)
    return {
        "total": len(items),
        "items": [
            {
                "id": str(e.id),
                "phase": e.phase,
                "label": e.label,
                "direction": e.direction,
                "action": e.action,
                "occurrences": e.occurrences,
            }
            for e in items
        ],
    }


@router.get(
    "/{project_id}/governance/policy-violations",
    summary="Policy/governance violations for the CISO view (CISO/Lead)",
)
async def policy_violations(
    project_id: uuid.UUID, db: DbSession, svc: Svc, _p: GovPrincipal
) -> dict[str, Any]:
    await _require_project(db, project_id)
    items = await svc.list_policy_violations(project_id)
    return {
        "total": len(items),
        "items": [
            {
                "id": str(v.id),
                "phase": v.phase,
                "policy": v.policy,
                "severity": v.severity,
                "detail": v.detail,
                "status": v.status,
            }
            for v in items
        ],
    }
