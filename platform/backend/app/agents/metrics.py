"""Per-persona metering aggregation over a set of phase runs.

Shared by the offline reference-metrics endpoint. Each phase maps to its owning persona (via the run's
own ``persona`` field); runs are grouped and summed into tokens, cost, and average latency.

``pricing_model`` lets a caller re-price the (deterministic) token counts at a chosen model so an
offline demo shows meaningful dollars even though the stub provider itself costs ``$0``. When omitted,
each run's own recorded ``cost_usd`` is used.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from app.agents.pricing import cost_usd


class _MeteredPhase(Protocol):
    persona: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_ms: float
    model: str


def metrics_by_persona(
    phases: Iterable[_MeteredPhase], *, pricing_model: str | None = None
) -> dict[str, Any]:
    """Aggregate phase metering by owning persona. Returns ``{personas, totals, pricing_model}``."""
    by_persona: dict[str, dict[str, Any]] = {}
    totals = {"runs": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "duration_ms": 0.0}

    for phase in phases:
        cost = (
            cost_usd(pricing_model, phase.input_tokens, phase.output_tokens)
            if pricing_model
            else phase.cost_usd
        )
        bucket = by_persona.setdefault(
            phase.persona,
            {"persona": phase.persona, "runs": 0, "input_tokens": 0, "output_tokens": 0,
             "cost_usd": 0.0, "duration_ms": 0.0},
        )
        bucket["runs"] += 1
        bucket["input_tokens"] += phase.input_tokens
        bucket["output_tokens"] += phase.output_tokens
        bucket["cost_usd"] += cost
        bucket["duration_ms"] += phase.duration_ms
        totals["runs"] += 1
        totals["input_tokens"] += phase.input_tokens
        totals["output_tokens"] += phase.output_tokens
        totals["cost_usd"] += cost
        totals["duration_ms"] += phase.duration_ms

    personas = []
    for bucket in sorted(by_persona.values(), key=lambda b: b["persona"]):
        runs = bucket["runs"] or 1
        bucket["cost_usd"] = round(bucket["cost_usd"], 6)
        bucket["avg_latency_ms"] = round(bucket["duration_ms"] / runs, 3)
        personas.append(bucket)
    totals["cost_usd"] = round(totals["cost_usd"], 6)
    return {"personas": personas, "totals": totals, "pricing_model": pricing_model or "actual"}
