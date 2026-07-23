"""ComplianceOfficerAgent — the governance-phase agent, running on the harness.

Demonstrates the harness's value in apex: the agent proposes a decision and a confidence; the harness
decides whether it may auto-enforce. A high-confidence policy breach auto-blocks; a borderline one is
routed to a human. The agent never enforces its own decision.
"""

from __future__ import annotations

from agent_harness import AuthorityLevel, Decision, DecisionAction
from agent_harness.core.agent import ToolInvoker
from agent_harness.ports.llm import Message

from .base import PhaseAgent
from .context import AgentContext

# A confident, material breach may auto-block; below this the harness routes to human review.
_BLOCK_CONFIDENCE = 0.95


class ComplianceOfficerAgent(PhaseAgent):
    """Assesses a change against policy and proposes ALLOW / ALERT / BLOCK / DEFER."""

    name = "compliance-officer"
    authority_level = AuthorityLevel.BLOCK
    capabilities = frozenset(
        {DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.BLOCK, DecisionAction.DEFER}
    )

    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        violations = int(ctx.inputs.get("policy_violations", 0))
        risk = float(ctx.inputs.get("risk_score", 0.0))
        rationale = self._assess(ctx, violations, risk)
        self._emit_governance_artifacts(ctx, violations, risk)

        if violations == 0:
            return Decision(DecisionAction.ALLOW, confidence=0.99, rationale=rationale)
        if risk >= _BLOCK_CONFIDENCE:
            return Decision(DecisionAction.BLOCK, confidence=risk, rationale=rationale)
        # Material but not certain — ALERT; the gate will route it to a human below its threshold.
        return Decision(DecisionAction.ALERT, confidence=risk, rationale=rationale)

    def _emit_governance_artifacts(self, ctx: AgentContext, violations: int, risk: float) -> None:
        feature = str(ctx.inputs.get("feature_name", "Change"))
        self.emit_artifact(
            name="governance-report.md",
            title=f"{feature} — Governance & Audit Report",
            kind="report",
            content=(
                f"# {feature} — Governance & Audit Report\n\n"
                f"- Policy violations: **{violations}**\n"
                f"- Composite risk score: **{risk:.2f}**\n"
                f"- Confidence gate: BLOCK auto-enforces only at ≥ 0.95; below that a human decides.\n"
                f"- Every phase decision in this project was recorded in the append-only audit log.\n"
            ),
        )
        self.emit_artifact(
            name="risk-register.md",
            title=f"{feature} — Risk Register",
            kind="analysis",
            content=(
                "# Risk Register\n\n"
                "| Risk | Likelihood | Impact | Mitigation |\n|---|---|---|---|\n"
                "| PII in logs (flagged in PR review) | Medium | High | Redact in web layer; PII guard |\n"
                "| SQL injection (flagged in PR review) | Low | Critical | Parameterised queries only |\n"
                "| Ledger posting lag | Medium | Medium | Outbox + retry; surface \"in progress\" |\n"
            ),
        )

    def _assess(self, ctx: AgentContext, violations: int, risk: float) -> str:
        prompt = (
            f"Phase {ctx.phase}: assess {violations} policy violation(s) at risk {risk:.2f}. "
            "Summarise the compliance position in one sentence."
        )
        try:
            return self.complete([Message(role="user", content=prompt)])
        except Exception:  # LLM failure is not fatal — the harness applies safe defaults around us
            return f"{violations} violation(s) at risk {risk:.2f} (LLM rationale unavailable)"
