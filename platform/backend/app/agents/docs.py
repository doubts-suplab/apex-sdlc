"""TechWriterAgent — the Docs-phase agent, running on the harness.

Primary persona: Developer / Technical Writer. It drafts an API reference and an onboarding guide
from the shipped service. SUGGEST authority → always routed to a human before publishing.
"""

from __future__ import annotations

from halo_agent_harness import AuthorityLevel, Decision, DecisionAction
from halo_agent_harness.core.agent import ToolInvoker
from halo_agent_harness.ports.llm import Message

from .base import PhaseAgent
from .context import AgentContext
from .prompts import DOCS_SYSTEM


class TechWriterAgent(PhaseAgent):
    """Drafts API reference + onboarding guide; proposes them for a human to publish."""

    name = "technical-writer"
    authority_level = AuthorityLevel.SUGGEST
    capabilities = frozenset({DecisionAction.SUGGEST, DecisionAction.DEFER})

    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        feature = str(ctx.inputs.get("feature_name", "Feature"))
        self.emit_artifact(
            name="api-reference.md",
            title=f"{feature} — API Reference",
            kind="api-doc",
            content=self.generate(
                prompt=self._api_prompt(feature),
                system=DOCS_SYSTEM,
                fallback=self._api(feature),
            ),
        )
        self.emit_artifact(
            name="onboarding-guide.md",
            title=f"{feature} — Onboarding Guide",
            kind="guide",
            content=self.generate(
                prompt=self._onboarding_prompt(feature),
                system=DOCS_SYSTEM,
                fallback=self._onboarding(feature),
            ),
        )
        return Decision(DecisionAction.SUGGEST, confidence=0.83, rationale=self._rationale(feature))

    # -- generation prompts (real provider; offline uses the fallbacks below) --
    def _api_prompt(self, feature: str) -> str:
        return (
            f"Write an API reference for '{feature}' documenting POST /api/v1/refunds (request, 202/409/422 "
            "responses, RFC 7807 problem details on error) in Markdown."
        )

    def _onboarding_prompt(self, feature: str) -> str:
        return (
            f"Write a short onboarding guide for '{feature}': docker compose up, run migrations, seed an "
            "order, call the refund endpoint, observe the outbox + audit entry."
        )

    # -- artifact builders (deterministic fallbacks) --------------------
    def _api(self, feature: str) -> str:
        return (
            f"# {feature} — API Reference\n\n"
            "## POST /api/v1/refunds\n"
            "Initiate a refund for an eligible order.\n\n"
            "**Request**\n```json\n"
            '{ "order_id": "ord_123", "refund_request_id": "rrq_abc" }\n```\n\n'
            "**Responses**\n"
            "- `202 Accepted` — refund initiated (asynchronous ledger posting).\n"
            "- `409 Conflict` — `already_refunded`.\n"
            "- `422 Unprocessable` — `window_expired`.\n\n"
            "All responses use RFC 7807 Problem Details on error.\n"
        )

    def _onboarding(self, feature: str) -> str:
        return (
            f"# {feature} — Onboarding Guide\n\n"
            "1. `docker compose up` (Postgres + service).\n"
            "2. Run migrations; seed a delivered order.\n"
            "3. `POST /api/v1/refunds` with an eligible `order_id`.\n"
            "4. Observe the outbox draining to the ledger and the audit entry written.\n"
        )

    def _rationale(self, feature: str) -> str:
        prompt = f"You are a technical writer. In one sentence, summarise the docs drafted for '{feature}'."
        try:
            return self.complete([Message(role="user", content=prompt)])
        except Exception:
            return (
                f"Drafted an API reference and onboarding guide for '{feature}'; "
                "routed to a human before publishing."
            )
