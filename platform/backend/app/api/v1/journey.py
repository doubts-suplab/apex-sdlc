"""Reference-journey API — serves the built-in POC walk through all SDLC phases.

Read-only and offline: it runs the orchestrator over the built-in reference project on each request
using the configured LLM provider (set ``LLM_PROVIDER=stub`` for a no-key demo). No DB access, so it
works even when Postgres/Redis are unavailable — the endpoint is the API face of the reference journey
that ``python -m app.demo.reference_journey`` writes to disk.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.agents.catalog import PERSONAS, phases_for_persona
from app.agents.orchestrator import run_reference_journey
from app.integrations.llm.factory import get_llm_provider

router = APIRouter(prefix="/journey", tags=["journey"])


def _journey() -> dict[str, Any]:
    return run_reference_journey(get_llm_provider()).to_dict()


@router.get("/reference", summary="Full reference journey (all phases)")
async def get_reference_journey(persona: str | None = None) -> dict[str, Any]:
    """Return the reference project's governed walk through every phase.

    Optionally filter to the phases a ``persona`` owns or contributes to/consumes.
    """
    data = _journey()
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
