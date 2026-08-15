"""PlanningAgent — proposes a project's next deliveries, running on the harness.

Where the phase agents produce SDLC artifacts, the planning agent produces a *plan*: a prioritized
list of proposed deliveries for one project. Its authority ceiling is ``SUGGEST`` — it proposes; a
human accepts. The harness enforces that: a ``SUGGEST`` decision never auto-enforces, so the proposed
deliveries land as ``status='proposed'`` for review rather than being committed autonomously.

The proposal is deterministic (derived from the project brief), so the offline reference journey stays
reproducible; a configured LLM provider only enriches the human-readable plan artifact, never the
structured deliveries.
"""

from __future__ import annotations

import re
from typing import Any

from halo_agent_harness import AuthorityLevel, Decision, DecisionAction
from halo_agent_harness.core.agent import ToolInvoker
from halo_agent_harness.ports.llm import LlmPort

from .base import PhaseAgent
from .context import AgentContext

# Priority + estimate ladder applied to the proposed backlog, highest-value first.
_PRIORITIES = ("high", "high", "medium", "medium", "low")
_ESTIMATES = (3, 5, 5, 8, 8)
_MAX_DELIVERIES = 5

# When a brief yields no goals, propose a sensible starter backlog so a plan is never empty.
_DEFAULT_GOALS = (
    "Define scope and acceptance criteria",
    "Implement the core capability",
    "Add test coverage",
)


class PlanningAgent(PhaseAgent):
    """Proposes a prioritized backlog of deliveries for a project (SUGGEST authority)."""

    name = "planning-agent"
    authority_level = AuthorityLevel.SUGGEST
    capabilities = frozenset({DecisionAction.SUGGEST, DecisionAction.DEFER})

    def __init__(self, llm: LlmPort) -> None:
        super().__init__(llm)
        self._proposed: list[dict[str, Any]] = []

    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        brief = str(ctx.inputs.get("brief", "")).strip()
        self._proposed = self._plan(brief)
        self._emit_plan_artifact(brief)
        rationale = f"Proposed {len(self._proposed)} deliveries from the project brief."
        # A plan is a suggestion — the harness routes it to human review; it never auto-enforces.
        return Decision(DecisionAction.SUGGEST, confidence=0.7, rationale=rationale)

    def proposed(self) -> list[dict[str, Any]]:
        """The structured deliveries proposed by the most recent run."""
        return list(self._proposed)

    # -- planning logic (deterministic) ---------------------------------
    def _plan(self, brief: str) -> list[dict[str, Any]]:
        goals = [g.strip() for g in re.split(r"[.;\n]+", brief) if g.strip()]
        if not goals:
            goals = list(_DEFAULT_GOALS)
        deliveries: list[dict[str, Any]] = []
        for i, goal in enumerate(goals[:_MAX_DELIVERIES]):
            deliveries.append(
                {
                    "title": goal[:255],
                    "description": "Proposed by the planning agent from the project brief.",
                    "priority": _PRIORITIES[min(i, len(_PRIORITIES) - 1)],
                    "estimate_points": _ESTIMATES[min(i, len(_ESTIMATES) - 1)],
                }
            )
        return deliveries

    def _emit_plan_artifact(self, brief: str) -> None:
        lines = ["# Proposed Delivery Plan", ""]
        if brief:
            lines += [f"> From brief: {brief[:200]}", ""]
        lines += ["| # | Title | Priority | Estimate |", "|---|---|---|---|"]
        for i, d in enumerate(self._proposed, start=1):
            lines.append(f"| {i} | {d['title']} | {d['priority']} | {d['estimate_points']} |")
        lines += ["", "_All deliveries are proposed (SUGGEST) — a human accepts them._"]
        self.emit_artifact(
            name="delivery-plan.md",
            title="Proposed Delivery Plan",
            kind="plan",
            content="\n".join(lines),
        )
