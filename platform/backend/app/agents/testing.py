"""QAAnalystAgent — the Testing-phase agent, running on the harness.

Primary persona: QA Engineer. It drafts a test plan, BDD test cases, and a coverage-gap analysis
from the approved stories. SUGGEST authority → always routed to a human for QA sign-off.
"""

from __future__ import annotations

from agent_harness import AuthorityLevel, Decision, DecisionAction
from agent_harness.core.agent import ToolInvoker
from agent_harness.ports.llm import Message

from .base import PhaseAgent
from .context import AgentContext


class QAAnalystAgent(PhaseAgent):
    """Drafts a test plan + BDD cases + coverage-gap analysis; proposes them for QA approval."""

    name = "qa-analyst"
    authority_level = AuthorityLevel.SUGGEST
    capabilities = frozenset({DecisionAction.SUGGEST, DecisionAction.DEFER})

    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        feature = str(ctx.inputs.get("feature_name", "Feature"))
        self.emit_artifact(
            name="test-plan.md",
            title=f"{feature} — Test Plan",
            kind="test-plan",
            content=self._plan(feature),
        )
        self.emit_artifact(
            name="test-cases.md",
            title=f"{feature} — Test Cases (BDD)",
            kind="test-cases",
            content=self._cases(feature),
        )
        self.emit_artifact(
            name="coverage-gaps.md",
            title=f"{feature} — Coverage Gap Analysis",
            kind="analysis",
            content=self._coverage(),
        )
        return Decision(DecisionAction.SUGGEST, confidence=0.85, rationale=self._rationale(feature))

    # -- artifact builders ----------------------------------------------
    def _plan(self, feature: str) -> str:
        return (
            f"# {feature} — Test Plan\n\n"
            f"Status: **[AI-Draft]** — awaiting QA sign-off (harness routed to human review).\n\n"
            f"| Aspect | Approach |\n|---|---|\n"
            f"| Scope | Refund eligibility, initiation, idempotency, rejection paths |\n"
            f"| Levels | Unit (domain), slice (web), integration (Testcontainers Postgres) |\n"
            f"| Entry | Stories approved, ADR signed off |\n"
            f"| Exit | 80% line / 70% branch, all rejection paths covered |\n"
            f"| Environments | Ephemeral Testcontainers; no production data |\n"
        )

    def _cases(self, feature: str) -> str:
        return (
            f"# {feature} — Test Cases (mapped to stories)\n\n"
            "| ID | Story | Given → When → Then | Type |\n"
            "|---|---|---|---|\n"
            "| TC-1 | Eligible refund | delivered in window → request → refund initiated | integration |\n"
            "| TC-2 | Window expired | delivered out of window → request → rejected(window_expired) | unit |\n"
            "| TC-3 | Already refunded | refunded order → request → rejected(already_refunded) | unit |\n"
            "| TC-4 | Idempotency | same refund_request_id twice → one refund | integration |\n"
        )

    def _coverage(self) -> str:
        return (
            "# Coverage Gap Analysis\n\n"
            "- Uncovered: `already_refunded` rejection branch (flagged by PR review too).\n"
            "- Uncovered: outbox publisher failure/retry path.\n"
            "- Suggested: add TC-3 (unit) and an outbox retry integration test.\n"
        )

    def _rationale(self, feature: str) -> str:
        prompt = f"You are a QA lead. In one sentence, summarise the test plan for '{feature}'."
        try:
            return self.complete([Message(role="user", content=prompt)])
        except Exception:
            return (
                f"Drafted a 4-case BDD suite and coverage-gap analysis for '{feature}'; "
                "routed to QA for sign-off."
            )
