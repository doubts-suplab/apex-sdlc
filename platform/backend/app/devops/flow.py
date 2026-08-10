"""DevOps flow — NL intent → plan → harness-gated multi-tool execution.

The :class:`DevOpsAgent` runs on the agent-harness. Two governance boundaries apply:

1. **Tool registry (hard, default-deny):** every tool call goes through the harness ``ToolInvoker``; a
   tool the agent was not granted raises ``ToolNotAuthorizedError`` before any side effect (spec §5).
2. **Confidence gate (auto-enforcement):** the agent proposes a Decision and a confidence; the harness
   sets ``auto_enforced``. This flow *ties side effects to that verdict* — it executes the write tools
   only when its confidence clears the auto-enforce bar for its authority; a low-confidence or ambiguous
   plan is **not executed**, it is emitted as a dry-run plan and routed to human review.

The agent never sets ``auto_enforced`` and never widens its own authority — the harness owns both.
"""

from __future__ import annotations

import json
from typing import Any

from halo_agent_harness import (
    AuthorityLevel,
    ConfidenceGate,
    Decision,
    DecisionAction,
    Harness,
)
from halo_agent_harness.core.agent import ToolInvoker
from halo_agent_harness.ports.llm import LlmPort

from app.agents.base import PhaseAgent
from app.agents.context import AgentContext, AgentResult
from app.agents.runtime import build_apex_harness, run_agent
from app.agents.tools import DEVOPS_AGENT_NAME, build_tool_registry
from app.devops.intent import PlannedCall, plan_from_intent

_HIGH_CONFIDENCE = 0.92  # a clean, fully-targeted plan
_AMBIGUOUS_CONFIDENCE = (
    0.7  # recognised intent but unresolved targets → human review, no side effects
)
_NO_PLAN_CONFIDENCE = 0.4  # no recognisable DevOps intent → defer


def _is_resolved(call: PlannedCall) -> bool:
    """A call is resolved when no argument still carries an ``UNSET`` placeholder target."""
    return not any("UNSET" in str(v) for v in call.arguments.values())


class DevOpsAgent(PhaseAgent):
    """Plans tool calls from an NL intent and executes them under the harness, gated by confidence."""

    name = DEVOPS_AGENT_NAME
    authority_level = AuthorityLevel.RATE_LIMIT
    capabilities = frozenset(
        {DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.SUGGEST, DecisionAction.DEFER}
    )

    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        intent = str(ctx.inputs.get("intent", "")).strip()
        context = {k: v for k, v in ctx.inputs.items() if k != "intent"}
        plan = plan_from_intent(intent, context=context)

        if not plan:
            self._emit_plan("devops-plan.md", intent, plan, executed=False, results=[])
            return Decision(
                DecisionAction.DEFER,
                confidence=_NO_PLAN_CONFIDENCE,
                rationale=f"No DevOps intent recognised in {intent!r}; deferring to a human.",
            )

        fully_resolved = all(_is_resolved(c) for c in plan)
        threshold = ConfidenceGate().threshold_for(self.authority_level)
        confidence = _HIGH_CONFIDENCE if fully_resolved else _AMBIGUOUS_CONFIDENCE
        will_execute = fully_resolved and confidence >= threshold

        if will_execute:
            results = self._execute(plan, tools, confidence)
            self._emit_plan("devops-execution-log.md", intent, plan, executed=True, results=results)
            return Decision(
                DecisionAction.ALLOW,
                confidence=confidence,
                rationale=f"Executed {len(results)} governed tool call(s) for {intent!r}.",
            )

        # Recognised but under-specified: propose the plan, take no action, route to a human.
        self._emit_plan("devops-plan.md", intent, plan, executed=False, results=[])
        return Decision(
            DecisionAction.SUGGEST,
            confidence=confidence,
            rationale=(
                f"Plan has unresolved targets (UNSET); proposing {len(plan)} call(s) for human review "
                "rather than executing."
            ),
        )

    def _execute(
        self, plan: list[PlannedCall], tools: ToolInvoker, confidence: float
    ) -> list[dict[str, Any]]:
        """Run each planned call through the harness ToolInvoker (default-deny enforced per call).

        Write/external tools are gated by the harness side-effect policy, which requires the
        invocation to carry a ``confidence`` clearing the side-effect threshold. We pass the flow's
        own vetted confidence — execution only reaches here when it already cleared the auto-enforce
        bar for this authority (``will_execute``).
        """
        results: list[dict[str, Any]] = []
        for call in plan:
            outcome = tools.call(call.tool, call.arguments, confidence=confidence)
            results.append({"tool": call.tool, "arguments": call.arguments, "result": outcome})
        return results

    def _emit_plan(
        self,
        name: str,
        intent: str,
        plan: list[PlannedCall],
        *,
        executed: bool,
        results: list[dict[str, Any]],
    ) -> None:
        status = (
            "executed under harness authorization"
            if executed
            else "held for human review — not executed"
        )
        lines = [
            f"# DevOps Flow — {'Execution Log' if executed else 'Proposed Plan (dry run)'}",
            "",
            f"**Intent:** {intent or '(empty)'}",
            f"**Status:** {status}",
            f"**Planned calls:** {len(plan)}",
            "",
        ]
        if executed:
            lines.append("| # | Tool | Result |")
            lines.append("|---|------|--------|")
            for i, r in enumerate(results, 1):
                summary = (
                    r["result"].get("url") or r["result"].get("key") or r["result"].get("ts", "")
                )
                lines.append(f"| {i} | `{r['tool']}` | {summary} |")
        else:
            lines.append("| # | Tool | Arguments |")
            lines.append("|---|------|-----------|")
            for i, c in enumerate(plan, 1):
                lines.append(f"| {i} | `{c.tool}` | `{json.dumps(c.arguments, sort_keys=True)}` |")
        self.emit_artifact(
            name=name,
            title="DevOps Flow — " + ("Execution Log" if executed else "Proposed Plan"),
            kind="log" if executed else "plan",
            content="\n".join(lines) + "\n",
        )
        self.emit_artifact(
            name=name.replace(".md", ".json"),
            title="DevOps Flow — machine-readable",
            kind="json",
            content=json.dumps(
                {
                    "intent": intent,
                    "executed": executed,
                    "calls": [{"tool": c.tool, "arguments": c.arguments} for c in plan],
                    "results": results,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            fmt="json",
        )


def run_devops_flow(
    *,
    llm: LlmPort,
    intent: str,
    context: dict[str, Any] | None = None,
    actor_id: str = "devops",
    adapters: dict[str, Any] | None = None,
    harness: Harness | None = None,
) -> AgentResult:
    """Build a governed harness, run the DevOps agent on an NL intent, and return the result.

    ``context`` supplies concrete targets (repo, jira_project_key, …). ``adapters`` overrides the offline
    tool implementations with a credentialed set of the same names to go live.
    """
    registry = build_tool_registry(adapters)
    harness = harness or build_apex_harness(registry=registry)
    agent = DevOpsAgent(llm)
    ctx = AgentContext(
        project_id=str((context or {}).get("project_id", "devops-demo")),
        phase="devops",
        actor_id=actor_id,
        inputs={"intent": intent, **(context or {})},
        run_id="devops-flow",
    )
    return run_agent(harness, agent, ctx)
