"""Agent-run API — run a single phase agent through the governed harness.

Offline-capable: builds a harness per request and runs the phase's agent via the same
``build_apex_harness`` / ``run_agent`` seam the orchestrator uses. Runs are kept in an in-process
store so ``GET /agents/{run_id}`` can return the outcome (a production build persists to ``agent_runs``).
"""

from __future__ import annotations

import uuid
from typing import Any

from agent_harness import ToolRegistry
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.catalog import PHASE_ORDER, spec_for
from app.agents.context import AgentContext
from app.agents.runtime import build_apex_harness, run_agent
from app.integrations.llm.factory import get_llm_provider

router = APIRouter(tags=["agents"])

# In-process run store (demo). A production build persists to the agent_runs table.
_RUNS: dict[str, dict[str, Any]] = {}


class AgentRunRequest(BaseModel):
    """Inputs for a phase agent run (e.g. feature_name, brief, version)."""

    actor_id: str = Field(default="system", description="Persona/user initiating the run")
    inputs: dict[str, Any] = Field(default_factory=dict)


def _run_payload(run_id: str, project_id: str, phase: str, result: Any, agent_name: str) -> dict[str, Any]:
    d = result.decision
    return {
        "run_id": run_id,
        "project_id": project_id,
        "phase": phase,
        "agent": agent_name,
        "status": result.status,
        "decision": {
            "action": d.action.value,
            "confidence": d.confidence,
            "auto_enforced": d.auto_enforced,
            "outcome": "auto-enforced" if d.auto_enforced else "human-review",
            "rationale": d.rationale,
        },
        "artifacts": result.artifacts,
    }


@router.post(
    "/projects/{project_id}/phases/{phase}/agents/run",
    summary="Run a phase agent through the harness",
)
async def run_phase_agent(project_id: str, phase: str, body: AgentRunRequest) -> dict[str, Any]:
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
    spec = spec_for(phase)
    run_id = str(uuid.uuid4())
    agent = spec.agent_cls(get_llm_provider())
    harness = build_apex_harness(registry=ToolRegistry())
    ctx = AgentContext(
        project_id=project_id,
        phase=phase,
        actor_id=body.actor_id,
        inputs=body.inputs,
        run_id=run_id,
    )
    result = run_agent(harness, agent, ctx)
    payload = _run_payload(run_id, project_id, phase, result, spec.agent_name)
    _RUNS[run_id] = payload
    return payload


@router.get("/agents/{run_id}", summary="Fetch a completed agent run")
async def get_agent_run(run_id: str) -> dict[str, Any]:
    payload = _RUNS.get(run_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/run-not-found",
                "title": "Agent run not found",
                "status": 404,
                "detail": f"No agent run with id={run_id} in this process.",
            },
        )
    return payload
