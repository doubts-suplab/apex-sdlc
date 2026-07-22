"""AgentContext / AgentResult and their mapping to the agent-harness envelope.

apex's phase-agent ergonomics (project/phase/actor) map onto the harness ``AgentInput`` /
``AgentOutput`` (tenant/user/decision). The project is apex's tenancy boundary for a run; the actor is
the user. See agent-harness ``docs/spec/harness-protocol.md`` §2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_harness import AgentInput, AgentOutput, Decision


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class AgentContext:
    """The context an apex phase agent runs against."""

    project_id: str
    phase: str
    actor_id: str
    inputs: dict[str, Any] = field(default_factory=dict)
    run_id: str = ""
    prompt_library: dict[str, str] = field(default_factory=dict)


@dataclass
class AgentResult:
    """The outcome apex records for a run — wraps the harness decision plus run bookkeeping."""

    run_id: str
    status: str  # "completed" | "failed"
    decision: Decision
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    error: str | None = None


def to_agent_input(ctx: AgentContext) -> AgentInput:
    """Map an apex AgentContext to a harness AgentInput (spec §2.1)."""
    return AgentInput(
        tenant_id=str(ctx.project_id),
        user_id=str(ctx.actor_id),
        context={"phase": ctx.phase, **ctx.inputs},
        metadata={
            "run_id": ctx.run_id,
            "phase": ctx.phase,
            "correlationId": ctx.run_id or f"{ctx.project_id}:{ctx.phase}",
        },
    )


def context_from_input(request: AgentInput) -> AgentContext:
    """Reconstruct an AgentContext inside an agent's ``run`` (inverse of ``to_agent_input``)."""
    inputs = {k: v for k, v in request.context.items() if k != "phase"}
    return AgentContext(
        project_id=request.tenant_id,
        actor_id=request.user_id,
        phase=str(request.context.get("phase", request.metadata.get("phase", ""))),
        inputs=inputs,
        run_id=str(request.metadata.get("run_id", "")),
    )


def to_agent_result(
    output: AgentOutput,
    ctx: AgentContext,
    *,
    status: str = "completed",
    artifacts: list[dict[str, Any]] | None = None,
    token_usage: TokenUsage | None = None,
    error: str | None = None,
) -> AgentResult:
    """Map a harness AgentOutput back to an apex AgentResult (spec §2.2)."""
    return AgentResult(
        run_id=ctx.run_id,
        status=status,
        decision=output.decision,
        artifacts=artifacts or [],
        token_usage=token_usage or TokenUsage(),
        error=error,
    )
