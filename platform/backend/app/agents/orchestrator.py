"""Journey orchestrator — run one project through all SDLC phases on the governed harness.

Iterates ``PHASE_CATALOG`` in order, instantiates each phase agent, and invokes it through the same
``build_apex_harness`` / ``run_agent`` seam the ComplianceOfficerAgent already uses. The harness — not
this orchestrator, not the agents — enforces the confidence gate, tool registry, audit, human review,
and safe-failure defaults on every phase. This module is pure in-memory: it needs no DB, no network,
and (with a stub LLM) no API keys, so the full journey runs offline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from agent_harness import ToolRegistry
from agent_harness.adapters import (
    InMemoryAudit,
    InMemoryHumanReview,
    InMemoryKillSwitch,
    InMemoryObservability,
)
from agent_harness.core.harness import BYPASS_COUNTER
from agent_harness.ports.llm import LlmPort

from .catalog import PHASE_CATALOG, PhaseSpec
from .context import AgentContext
from .runtime import build_apex_harness, run_agent


@dataclass
class JourneyPhase:
    """The governed outcome of one phase in the journey."""

    phase: str
    label: str
    persona: str
    stakeholders: list[str]
    agent_name: str
    authority: str
    action: str
    confidence: float
    auto_enforced: bool
    outcome: str  # "auto-enforced" | "human-review"
    rationale: str
    eeik_agent: str
    summary: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class JourneyResult:
    """The full walk of a project through every SDLC phase, plus governance stats."""

    project: dict[str, Any]
    phases: list[JourneyPhase]
    stats: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "phases": [asdict(p) for p in self.phases],
            "stats": self.stats,
        }


# The reference project the demo/journey walks. A relatable enterprise/payments example that also
# exercises PII and governance. Adjustable — nothing downstream hard-codes these values.
REFERENCE_PROJECT: dict[str, Any] = {
    "name": "Customer Refunds Service",
    "slug": "refund-service",
    "description": "A Spring Boot microservice that lets customers self-serve refunds on eligible orders.",
    "stack": "Spring Boot 3.x / Java 21 / PostgreSQL",
    "feature_name": "Customer Refunds",
    "version": "v1.0.0",
    "brief": (
        "Let customers request a refund on a delivered order without contacting support. "
        "Refunds must be eligibility-checked server-side, auditable, idempotent, and must never "
        "leak customer PII."
    ),
    # Governance-phase inputs represent the two golden-rule breaches the PR review flagged
    # (SQL-injection risk + PII in logs) at a borderline risk score — enough to ALERT, not auto-block.
    "policy_violations": 2,
    "risk_score": 0.6,
    "checks_green": True,
}


def run_journey(project: dict[str, Any], llm: LlmPort, *, registry: ToolRegistry | None = None) -> JourneyResult:
    """Run ``project`` through every phase in ``PHASE_CATALOG`` on one harness; collect the outcomes."""
    audit, review, obs, kill = (
        InMemoryAudit(),
        InMemoryHumanReview(),
        InMemoryObservability(),
        InMemoryKillSwitch(),
    )
    harness = build_apex_harness(
        registry=registry or ToolRegistry(),
        audit=audit,
        human_review=review,
        observability=obs,
        kill_switch=kill,
    )

    phases: list[JourneyPhase] = []
    for spec in PHASE_CATALOG:
        result = _run_phase(harness, spec, project, llm)
        phases.append(result)

    auto = sum(1 for p in phases if p.auto_enforced)
    stats = {
        "phase_count": len(phases),
        "auto_enforced_count": auto,
        "human_review_count": len(phases) - auto,
        "artifact_count": sum(len(p.artifacts) for p in phases),
        "audit_entries": len(audit.entries),
        # spec §4.2: this counter MUST stay 0 — a non-zero value is a governance incident.
        "confidence_gate_bypass_total": obs.counter(BYPASS_COUNTER),
    }
    return JourneyResult(project=_project_summary(project), phases=phases, stats=stats)


def _run_phase(harness: Any, spec: PhaseSpec, project: dict[str, Any], llm: LlmPort) -> JourneyPhase:
    agent = spec.agent_cls(llm)  # fresh instance per phase
    ctx = AgentContext(
        project_id=str(project.get("slug", "project")),
        phase=spec.phase,
        actor_id=spec.primary_persona,
        inputs=project,
        run_id=f"{project.get('slug', 'project')}:{spec.phase}",
    )
    result = run_agent(harness, agent, ctx)
    decision = result.decision
    return JourneyPhase(
        phase=spec.phase,
        label=spec.label,
        persona=spec.primary_persona,
        stakeholders=list(spec.stakeholders),
        agent_name=spec.agent_name,
        authority=spec.authority.name,
        action=decision.action.value,
        confidence=decision.confidence,
        auto_enforced=decision.auto_enforced,
        outcome="auto-enforced" if decision.auto_enforced else "human-review",
        rationale=decision.rationale,
        eeik_agent=spec.eeik_agent,
        summary=spec.summary,
        artifacts=result.artifacts,
    )


def run_reference_journey(llm: LlmPort) -> JourneyResult:
    """Convenience: run the built-in REFERENCE_PROJECT through the full lifecycle."""
    return run_journey(REFERENCE_PROJECT, llm)


def _project_summary(project: dict[str, Any]) -> dict[str, Any]:
    keys = ("name", "slug", "description", "stack", "feature_name", "version")
    return {k: project[k] for k in keys if k in project}
