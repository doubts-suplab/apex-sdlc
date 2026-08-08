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

from .authority import confidence_threshold
from .catalog import PHASE_CATALOG, PhaseSpec, spec_for
from .context import AgentContext
from .pricing import cost_usd
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
    # The confidence the agent had to clear to auto-enforce, or None if this phase can never auto-enforce
    # (gate rule G-5: SUGGEST/OBSERVE always route to a human). Derived from the harness confidence gate.
    confidence_threshold: float | None
    auto_enforced: bool
    outcome: str  # "auto-enforced" | "human-review"
    rationale: str
    eeik_agent: str
    summary: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    # Metering — captured in-memory for persistence; intentionally NOT serialized to the committed
    # journey.json (duration_ms is wall-clock and would break the reference example's determinism).
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    model: str = ""
    provider: str = ""
    pii_findings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class JourneyResult:
    """The full walk of a project through every SDLC phase, plus governance stats."""

    project: dict[str, Any]
    phases: list[JourneyPhase]
    stats: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        # Serialize the stable, deterministic subset only — metering fields (tokens/cost/duration) are
        # kept in-memory for persistence but excluded here so the committed journey.json stays reproducible.
        stable = {
            "phase", "label", "persona", "stakeholders", "agent_name", "authority", "action",
            "confidence", "confidence_threshold", "auto_enforced", "outcome", "rationale",
            "eeik_agent", "summary", "artifacts",
        }
        return {
            "project": self.project,
            "phases": [{k: v for k, v in asdict(p).items() if k in stable} for p in self.phases],
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


def _fresh_harness(
    registry: ToolRegistry | None = None,
) -> tuple[Any, InMemoryAudit, InMemoryObservability]:
    """Build a governed harness with in-memory adapters; return it with the audit + obs sinks."""
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
    return harness, audit, obs


def run_single_phase(
    project: dict[str, Any],
    phase: str,
    llm: LlmPort,
    *,
    registry: ToolRegistry | None = None,
) -> JourneyPhase:
    """Run one phase's agent for ``project`` on a fresh governed harness; return its outcome.

    The execution primitive behind an event-driven trigger (a webhook dispatch that resolved to a
    project + phase). Same ``build_apex_harness`` / ``run_agent`` seam as the full journey — the
    harness still owns the confidence gate, tool registry, audit, and safe-failure defaults.
    """
    harness, _audit, _obs = _fresh_harness(registry)
    return _run_phase(harness, spec_for(phase), project, llm)


def run_journey(project: dict[str, Any], llm: LlmPort, *, registry: ToolRegistry | None = None) -> JourneyResult:
    """Run ``project`` through every phase in ``PHASE_CATALOG`` on one harness; collect the outcomes."""
    harness, audit, obs = _fresh_harness(registry)

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
        confidence_threshold=confidence_threshold(spec),
        auto_enforced=decision.auto_enforced,
        outcome="auto-enforced" if decision.auto_enforced else "human-review",
        rationale=decision.rationale,
        eeik_agent=spec.eeik_agent,
        summary=spec.summary,
        artifacts=result.artifacts,
        input_tokens=result.token_usage.input_tokens,
        output_tokens=result.token_usage.output_tokens,
        cost_usd=cost_usd(
            result.model, result.token_usage.input_tokens, result.token_usage.output_tokens
        ),
        duration_ms=result.duration_ms,
        model=result.model,
        provider=result.provider,
        pii_findings=result.pii_findings,
    )


def run_reference_journey(llm: LlmPort) -> JourneyResult:
    """Convenience: run the built-in REFERENCE_PROJECT through the full lifecycle."""
    return run_journey(REFERENCE_PROJECT, llm)


def _project_summary(project: dict[str, Any]) -> dict[str, Any]:
    keys = ("name", "slug", "description", "stack", "feature_name", "version")
    return {k: project[k] for k in keys if k in project}
