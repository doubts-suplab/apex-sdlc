"""PRReviewerAgent — the Development-phase agent, running on the harness.

Primary persona: Developer. It reviews a PR diff and emits ALLOW (clean) or ALERT (issues found).
ALERT authority auto-enforces at confidence >= 0.80 (the harness posts the advisory review); a
borderline ALERT is routed to a human. The agent never decides its own enforcement.
"""

from __future__ import annotations

from agent_harness import AuthorityLevel, Decision, DecisionAction
from agent_harness.core.agent import ToolInvoker
from agent_harness.ports.llm import Message

from .base import PhaseAgent
from .context import AgentContext


class PRReviewerAgent(PhaseAgent):
    """Reviews a diff; ALLOW when clean, ALERT (advisory) when it finds issues."""

    name = "pr-reviewer"
    authority_level = AuthorityLevel.ALERT
    capabilities = frozenset({DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.DEFER})

    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        feature = str(ctx.inputs.get("feature_name", "Feature"))
        findings = self._findings(ctx)
        self.emit_artifact(
            name="pr-review.md",
            title=f"{feature} — PR Review",
            kind="review",
            content=self._review(feature, findings),
        )
        self.emit_artifact(
            name="quality-report.md",
            title=f"{feature} — Code Quality Report",
            kind="report",
            content=self._quality(findings),
        )
        if not findings:
            return Decision(
                DecisionAction.ALLOW,
                confidence=0.9,
                rationale="No blocking issues found in the diff; approving the change.",
            )
        # Issues found → advisory ALERT. High confidence auto-enforces (harness posts the review).
        return Decision(DecisionAction.ALERT, confidence=0.88, rationale=self._rationale(feature, findings))

    # -- analysis --------------------------------------------------------
    def _findings(self, ctx: AgentContext) -> list[str]:
        # Deterministic sample findings for the reference journey; a real run reads the diff via a tool.
        return [
            "RefundService.initiate() builds SQL by string concatenation — use a parameterised query.",
            "Customer email is logged at INFO in RefundController — PII must not be logged.",
            "No test covers the 'already_refunded' rejection path.",
        ]

    def _review(self, feature: str, findings: list[str]) -> str:
        if not findings:
            body = "No blocking issues found. Approving.\n"
        else:
            body = "".join(f"- **[MAJOR]** {f}\n" for f in findings)
        return (
            f"# {feature} — PR Review\n\n"
            f"> Advisory review by the PR Reviewer agent (harness authority: ALERT). "
            f"Auto-enforced advisory posting when confident; a human still merges.\n\n"
            f"{body}"
        )

    def _quality(self, findings: list[str]) -> str:
        return (
            "# Code Quality Report\n\n"
            f"- Findings: **{len(findings)}**\n"
            "- Golden-rule checks: parameterised-queries **FAIL**, no-PII-in-logs **FAIL**, "
            "test-coverage **WARN**\n"
            "- Risk areas: refund initiation path, logging in the web layer\n"
        )

    def _rationale(self, feature: str, findings: list[str]) -> str:
        prompt = (
            f"You are a senior reviewer. In one sentence, summarise a PR review of '{feature}' that "
            f"found {len(findings)} issues."
        )
        try:
            return self.complete([Message(role="user", content=prompt)])
        except Exception:
            return (
                f"Found {len(findings)} issues in the '{feature}' PR (SQL injection risk, PII in logs, "
                "missing test); posted an advisory review."
            )
