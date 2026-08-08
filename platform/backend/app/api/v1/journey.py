"""Reference-journey API — serves the built-in POC walk through all SDLC phases.

Read-only and offline: it runs the orchestrator over the built-in reference project on each request
using the configured LLM provider (set ``LLM_PROVIDER=stub`` for a no-key demo). No DB access, so it
works even when Postgres/Redis are unavailable — the endpoint is the API face of the reference journey
that ``python -m app.demo.reference_journey`` writes to disk.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.agents.authority import authority_model
from app.agents.catalog import PERSONAS, phases_for_persona
from app.agents.metrics import metrics_by_persona
from app.agents.orchestrator import run_reference_journey
from app.gates.engine import evaluate_journey
from app.integrations.llm.factory import get_llm_provider
from app.spine.config import SpineConfig, SpineConfigError, build_spine, default_spine

router = APIRouter(prefix="/journey", tags=["journey"])

# Reference/illustrative pricing model for the offline dashboard: the deterministic stub token counts are
# priced at this model's rates so the demo shows meaningful dollars (the stub itself costs $0).
_DEFAULT_PRICING_MODEL = "claude-opus-4-8"


def _spine_from_query(phases: str | None) -> SpineConfig:
    """Build a SpineConfig from a ``phases`` CSV query param, or the full default spine when absent.

    A malformed/unknown phase list is a 400 (RFC-7807) rather than a 500 — it is user input.
    """
    if phases is None:
        return default_spine()
    wanted = [p.strip() for p in phases.split(",") if p.strip()]
    try:
        return build_spine(wanted)
    except SpineConfigError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "https://apex.example.com/problems/invalid-spine",
                "title": "Invalid spine configuration",
                "status": 400,
                "detail": str(exc),
            },
        ) from exc


def _journey() -> dict[str, Any]:
    return run_reference_journey(get_llm_provider()).to_dict()


@router.get("/reference", summary="Reference journey (all phases, or a configured spine subset)")
async def get_reference_journey(
    persona: str | None = None, phases: str | None = None
) -> dict[str, Any]:
    """Return the reference project's governed walk through the configured spine.

    ``phases`` is an optional comma-separated subset of the seven catalog phases (e.g.
    ``requirements,architecture,development``) — the configurable-spine control for orgs that don't want
    the full model. Absent ⇒ the full seven-phase spine. ``persona`` further filters to the phases a
    persona owns or contributes to/consumes.
    """
    spine = _spine_from_query(phases)
    data = run_reference_journey(get_llm_provider(), spine=spine).to_dict()
    if persona is not None:
        if persona not in PERSONAS:
            raise HTTPException(
                status_code=404,
                detail={
                    "type": "https://apex.example.com/problems/unknown-persona",
                    "title": "Unknown persona",
                    "status": 404,
                    "detail": f"Persona {persona!r} is not one of {list(PERSONAS)}.",
                },
            )
        wanted = {s.phase for s in phases_for_persona(persona)}
        data = {**data, "phases": [p for p in data["phases"] if p["phase"] in wanted], "persona": persona}
    return data


@router.get("/authority", summary="Authority ladder + per-phase confidence thresholds (gate rule G-5)")
async def get_authority_model() -> dict[str, Any]:
    """Return the governance read model: the G-5 rule, the authority ladder, and each phase's
    confidence-gate threshold (``null`` where the phase can never auto-enforce). Catalog + harness
    derived — no DB, no LLM run, safe offline.
    """
    return authority_model()


@router.get("/reference/gates", summary="Evaluate the spine's phase gates across the reference journey")
async def get_reference_gates(
    approved: str | None = None, phases: str | None = None
) -> dict[str, Any]:
    """Evaluate every phase gate for the reference journey (optionally a configured spine subset).

    ``approved`` is a comma-separated list of phases whose spec a human has approved (human-review phases
    stay ``pending`` until approved). ``phases`` optionally restricts the spine to a subset (the same
    control as ``/reference``), so the gate evaluation matches the configured model. The response's
    ``blocking_phase`` is where the spine halts.
    """
    spine = _spine_from_query(phases)
    approvals = {p.strip() for p in approved.split(",")} if approved else set()
    journey = run_reference_journey(get_llm_provider(), spine=spine)
    return {
        "project": journey.project,
        "phases": list(spine.phases),
        "approved": sorted(approvals),
        **evaluate_journey(journey, approvals, spine=spine),
    }


@router.get("/reference/metrics", summary="Per-persona cost / token / latency for the reference journey")
async def get_reference_metrics(model: str | None = None) -> dict[str, Any]:
    """Aggregate the reference journey's metering per persona (the offline cost/latency dashboard).

    Token counts and latency are real (the stub yields deterministic tokens); ``model`` sets the pricing
    used for the illustrative ``cost_usd`` (defaults to a reference model so the demo shows dollars).
    """
    journey = run_reference_journey(get_llm_provider())
    pricing_model = model or _DEFAULT_PRICING_MODEL
    return {"project": journey.project, **metrics_by_persona(journey.phases, pricing_model=pricing_model)}


@router.get("/reference/artifacts/{phase}", summary="Artifacts produced in one phase")
async def get_phase_artifacts(phase: str) -> dict[str, Any]:
    """Return the artifacts the reference journey produced for a single phase."""
    data = _journey()
    match = next((p for p in data["phases"] if p["phase"] == phase), None)
    if match is None:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "https://apex.example.com/problems/unknown-phase",
                "title": "Unknown phase",
                "status": 404,
                "detail": f"Phase {phase!r} is not part of the reference journey.",
            },
        )
    return {"phase": phase, "label": match["label"], "artifacts": match["artifacts"]}
