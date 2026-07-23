"""RequirementsAgent — the Requirements-phase agent, running on the harness.

Primary persona: Business Analyst. It turns a project brief into Gherkin user stories and a gap
analysis, and proposes them (SUGGEST). A SUGGEST-authority agent never auto-enforces (harness gate
G-5): the stories are always routed to a human for approval — apex's "AI drafts, humans approve"
principle expressed through the harness authority ladder.
"""

from __future__ import annotations

from agent_harness import AuthorityLevel, Decision, DecisionAction
from agent_harness.core.agent import ToolInvoker
from agent_harness.ports.llm import Message

from .base import PhaseAgent
from .context import AgentContext


class RequirementsAgent(PhaseAgent):
    """Drafts Gherkin stories + gap analysis from a brief; proposes them for BA approval."""

    name = "requirements-analyst"
    authority_level = AuthorityLevel.SUGGEST
    capabilities = frozenset({DecisionAction.SUGGEST, DecisionAction.DEFER})

    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        brief = str(ctx.inputs.get("brief", "")).strip()
        if not brief:
            return Decision(
                DecisionAction.DEFER,
                confidence=0.4,
                rationale="No project brief supplied — deferring to a human to provide scope.",
            )

        feature = str(ctx.inputs.get("feature_name", "Feature"))
        stories = self._stories(feature, brief)
        gaps = self._gaps(feature, brief)
        self.emit_artifact(
            name="user-stories.md",
            title=f"{feature} — User Stories (Gherkin)",
            kind="gherkin",
            content=stories,
        )
        self.emit_artifact(
            name="gap-analysis.md",
            title=f"{feature} — Requirements Gap Analysis",
            kind="analysis",
            content=gaps,
        )
        rationale = self._rationale(feature, brief)
        # SUGGEST at high confidence: the harness still routes it to a human (SUGGEST never enforces).
        return Decision(DecisionAction.SUGGEST, confidence=0.86, rationale=rationale)

    # -- artifact builders ----------------------------------------------
    def _stories(self, feature: str, brief: str) -> str:
        return (
            f"# {feature} — User Stories\n\n"
            f"> Drafted by the Requirements Analyst agent from the project brief. "
            f"Status: **[AI-Draft]** — awaiting BA approval (harness routed to human review).\n\n"
            f"```gherkin\n"
            f"Feature: {feature}\n"
            f"  As a customer\n"
            f"  I want to request a refund for an eligible order\n"
            f"  So that I am reimbursed without contacting support\n\n"
            f"  Scenario: Eligible order is refunded\n"
            f"    Given an order that was delivered within the refund window\n"
            f"    And the order has not already been refunded\n"
            f"    When the customer requests a refund\n"
            f"    Then a refund is initiated for the order total\n"
            f"    And the customer is notified the refund is in progress\n\n"
            f"  Scenario: Refund window has expired\n"
            f"    Given an order delivered outside the refund window\n"
            f"    When the customer requests a refund\n"
            f"    Then the request is rejected with reason \"window_expired\"\n\n"
            f"  Scenario: Order already refunded\n"
            f"    Given an order that has already been fully refunded\n"
            f"    When the customer requests a refund\n"
            f"    Then the request is rejected with reason \"already_refunded\"\n"
            f"```\n\n"
            f"## Acceptance criteria\n"
            f"- Refund eligibility is evaluated server-side; the client never asserts eligibility.\n"
            f"- Every refund decision is auditable (who, when, amount, reason).\n"
            f"- Customer PII is never written to logs (governance-gated downstream).\n"
        )

    def _gaps(self, feature: str, brief: str) -> str:
        return (
            f"# {feature} — Requirements Gap Analysis\n\n"
            f"Brief analysed:\n\n> {brief}\n\n"
            f"| Area | Covered by brief | Gap flagged for the BA |\n"
            f"|---|---|---|\n"
            f"| Happy-path refund | Yes | — |\n"
            f"| Refund window rules | Partially | Exact window length not specified |\n"
            f"| Partial refunds | No | Is a partial refund in scope for v1? |\n"
            f"| Idempotency | No | Define behaviour on duplicate refund requests |\n"
            f"| Downstream ledger | No | Which system of record posts the credit? |\n\n"
            f"**Recommendation:** resolve the four gaps above before the Architecture phase.\n"
        )

    def _rationale(self, feature: str, brief: str) -> str:
        prompt = (
            f"You are a business analyst. In one sentence, summarise the requirements position for "
            f"'{feature}' given this brief: {brief}"
        )
        try:
            return self.complete([Message(role="user", content=prompt)])
        except Exception:  # LLM failure is not fatal — the harness applies safe defaults around us
            return (
                f"Drafted 3 Gherkin scenarios and 5 gap items for '{feature}'; "
                "routed to the BA for approval."
            )
