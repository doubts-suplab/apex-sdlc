"""Runtime wiring — build an apex-configured harness and run a phase agent through it.

This is the seam a Celery task / agent service calls: map the apex AgentContext to the harness envelope,
invoke through the governed harness, and map the result back. All governance (gate, tool registry,
audit, human review, observability, safe-failure) is enforced by the harness, not re-implemented here.
"""

from __future__ import annotations

from agent_harness import Harness, ToolRegistry
from agent_harness.ports.governance import (
    AuditPort,
    HumanReviewPort,
    KillSwitchPort,
    ObservabilityPort,
)

from .adapters import FlagKillSwitch, StructlogAudit, StructlogHumanReview, StructlogObservability
from .base import PhaseAgent
from .context import AgentContext, AgentResult, to_agent_input, to_agent_result


def build_apex_harness(
    *,
    registry: ToolRegistry | None = None,
    audit: AuditPort | None = None,
    human_review: HumanReviewPort | None = None,
    observability: ObservabilityPort | None = None,
    kill_switch: KillSwitchPort | None = None,
) -> Harness:
    """Construct a Harness wired with apex's default (structlog) adapters, overridable for tests."""
    return Harness(
        registry or ToolRegistry(),
        audit=audit or StructlogAudit(),
        human_review=human_review or StructlogHumanReview(),
        observability=observability or StructlogObservability(),
        kill_switch=kill_switch or FlagKillSwitch(),
    )


def run_agent(harness: Harness, agent: PhaseAgent, ctx: AgentContext) -> AgentResult:
    """Invoke a phase agent through the harness and return an apex AgentResult."""
    output = harness.invoke(agent, to_agent_input(ctx))
    return to_agent_result(output, ctx)
