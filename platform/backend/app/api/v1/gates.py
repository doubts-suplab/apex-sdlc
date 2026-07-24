"""Phase-gate API — evaluate whether a phase may transition (ROADMAP Phase 5).

Offline and DB-free: the engine is pure, so evaluation takes explicit inputs. Persisting evaluations to
the ``phase_gates`` table is a separate concern.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.catalog import PHASE_ORDER
from app.gates.engine import evaluate_gate

router = APIRouter(tags=["gates"])


class GateEvaluationRequest(BaseModel):
    """Inputs to evaluate a phase's gate."""

    produced_artifacts: list[str] = Field(default_factory=list)
    auto_enforced: bool = False
    approved: bool = False
    bypass_total: int = 0


@router.post(
    "/projects/{project_id}/phases/{phase}/gate/evaluate",
    summary="Evaluate a phase gate — pass / pending / fail",
)
async def evaluate_phase_gate(
    project_id: str, phase: str, body: GateEvaluationRequest
) -> dict[str, Any]:
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
    return {"project_id": project_id, **result.to_dict()}
