"""Persistence API — persist a project's governed journey and read the stored state back.

``POST /projects/{id}/journey/persist`` runs the reference journey for a project and stores its agent
runs, artifacts, and phase gates; the ``GET`` endpoints read them. Requires a database (production path).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agents.orchestrator import run_reference_journey
from app.core.security import Principal, require_persona
from app.db.session import DbSession
from app.integrations.llm.factory import get_llm_provider
from app.services.persistence_service import PersistenceService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["persistence"])

# Personas allowed to run + approve a journey (a spec-approval / gate action). Read endpoints stay
# open for now; global auth enforcement on every route is the follow-on (see docs/progress.md).
_APPROVER_PERSONAS = ("lead", "ba", "architect", "ciso")


def _svc(db: DbSession) -> PersistenceService:
    return PersistenceService(db)


Svc = Annotated[PersistenceService, Depends(_svc)]


async def _require_project(db: DbSession, project_id: uuid.UUID) -> None:
    if await ProjectService(db).get_by_id(project_id) is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/project-not-found",
                "title": "Project Not Found",
                "status": 404,
                "detail": f"No project with id={project_id} exists.",
            },
        )


@router.post("/{project_id}/journey/persist", summary="Run + persist the reference journey for a project")
async def persist_journey(
    project_id: uuid.UUID,
    db: DbSession,
    svc: Svc,
    principal: Annotated[Principal, Depends(require_persona(*_APPROVER_PERSONAS))],
    approved: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    await _require_project(db, project_id)
    approvals = {p.strip() for p in approved.split(",")} if approved else set()
    journey = run_reference_journey(get_llm_provider())
    return await svc.persist_journey(project_id, journey, approvals)


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
