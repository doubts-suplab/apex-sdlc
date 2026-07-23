"""ArchitectureAgent — the Architecture-phase agent, running on the harness.

Primary persona: Architect. It proposes an ADR and a component diagram from the approved
requirements. SUGGEST authority → the harness always routes the ADR to a human for sign-off
(no self-enforced architecture).
"""

from __future__ import annotations

from agent_harness import AuthorityLevel, Decision, DecisionAction
from agent_harness.core.agent import ToolInvoker
from agent_harness.ports.llm import Message

from .base import PhaseAgent
from .context import AgentContext


class ArchitectureAgent(PhaseAgent):
    """Drafts an ADR + component diagram + tech-debt note; proposes them for architect sign-off."""

    name = "solution-architect"
    authority_level = AuthorityLevel.SUGGEST
    capabilities = frozenset({DecisionAction.SUGGEST, DecisionAction.DEFER})

    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        feature = str(ctx.inputs.get("feature_name", "Feature"))
        stack = str(ctx.inputs.get("stack", "Spring Boot 3.x / Java 21 / PostgreSQL"))
        self.emit_artifact(
            name="ADR-0001-refund-service.md",
            title=f"ADR-0001 — {feature} bounded context",
            kind="adr",
            content=self._adr(feature, stack),
        )
        self.emit_artifact(
            name="component-diagram.mmd",
            title=f"{feature} — Component Diagram",
            kind="mermaid",
            content=self._diagram(feature),
            fmt="mermaid",
        )
        self.emit_artifact(
            name="tech-debt.md",
            title=f"{feature} — Tech-Debt Register",
            kind="analysis",
            content=self._tech_debt(),
        )
        return Decision(DecisionAction.SUGGEST, confidence=0.84, rationale=self._rationale(feature, stack))

    # -- artifact builders ----------------------------------------------
    def _adr(self, feature: str, stack: str) -> str:
        return (
            f"# ADR-0001 — {feature} bounded context\n\n"
            f"Status: **Proposed** (awaiting architect sign-off — harness routed to human review)\n\n"
            f"## Context\n"
            f"{feature} must evaluate refund eligibility server-side, initiate a credit, and remain "
            f"auditable. It integrates with the orders read-model and a downstream ledger.\n\n"
            f"## Decision\n"
            f"- Implement as a standalone Spring Boot service ({stack}) with a hexagonal layering "
            f"(domain / application / infrastructure / web).\n"
            f"- Own a `refunds` bounded context; read order state via an anti-corruption port, never a "
            f"cross-context DB join.\n"
            f"- Enforce idempotency with a client-supplied `refund_request_id` unique key.\n"
            f"- Post the credit to the ledger through an outbox + async publisher (no dual-write).\n\n"
            f"## Consequences\n"
            f"- (+) Clear ownership, auditable decisions, no distributed transaction.\n"
            f"- (−) Eventual consistency between refund initiation and ledger posting; surfaced to the "
            f"customer as \"in progress\".\n"
        )

    def _diagram(self, feature: str) -> str:
        return (
            "graph LR\n"
            "  Client[Customer app] -->|POST /refunds| API[Refund API]\n"
            "  API --> Domain[Refund domain]\n"
            "  Domain -->|eligibility| Orders[(Orders read-model)]\n"
            "  Domain --> Outbox[(Outbox)]\n"
            "  Outbox -->|async| Ledger[Ledger service]\n"
            "  Domain --> Audit[(Audit log)]\n"
        )

    def _tech_debt(self) -> str:
        return (
            "# Tech-Debt Register\n\n"
            "| Item | Priority | Target sprint |\n"
            "|---|---|---|\n"
            "| Outbox publisher lacks dead-letter handling | High | Next |\n"
            "| Orders read-model polled, not event-driven | Medium | +2 |\n"
        )

    def _rationale(self, feature: str, stack: str) -> str:
        prompt = (
            f"You are a solution architect. In one sentence, justify a standalone hexagonal "
            f"{stack} service for '{feature}'."
        )
        try:
            return self.complete([Message(role="user", content=prompt)])
        except Exception:
            return (
                f"Proposed a standalone hexagonal {feature} service with idempotent refunds and an "
                "outbox to the ledger; routed to the architect for sign-off."
            )
