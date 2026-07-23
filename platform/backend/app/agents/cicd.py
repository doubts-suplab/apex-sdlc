"""ReleaseEngineerAgent — the CI/CD-phase agent, running on the harness.

Primary persona: Tech Lead / Release Engineer. It assembles release notes, a deployment checklist,
and a rollback plan, then proposes ALLOW (release) or ALERT (hold). RATE_LIMIT authority auto-enforces
ALLOW at confidence >= 0.85; below that the release is routed to a human.
"""

from __future__ import annotations

from agent_harness import AuthorityLevel, Decision, DecisionAction
from agent_harness.core.agent import ToolInvoker
from agent_harness.ports.llm import Message

from .base import PhaseAgent
from .context import AgentContext


class ReleaseEngineerAgent(PhaseAgent):
    """Assembles release artifacts; ALLOW to release when checks pass, ALERT to hold otherwise."""

    name = "release-engineer"
    authority_level = AuthorityLevel.RATE_LIMIT
    capabilities = frozenset({DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.DEFER})

    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision:
        feature = str(ctx.inputs.get("feature_name", "Feature"))
        version = str(ctx.inputs.get("version", "v1.0.0"))
        checks_green = bool(ctx.inputs.get("checks_green", True))
        self.emit_artifact(
            name="release-notes.md",
            title=f"{feature} — Release Notes {version}",
            kind="release-notes",
            content=self._notes(feature, version),
        )
        self.emit_artifact(
            name="deployment-checklist.md",
            title=f"{feature} — Deployment Checklist",
            kind="checklist",
            content=self._checklist(),
        )
        self.emit_artifact(
            name="rollback-plan.md",
            title=f"{feature} — Rollback Plan",
            kind="runbook",
            content=self._rollback(version),
        )
        if not checks_green:
            return Decision(
                DecisionAction.ALERT,
                confidence=0.9,
                rationale="CI checks are not green — holding the release for a human.",
            )
        return Decision(DecisionAction.ALLOW, confidence=0.88, rationale=self._rationale(feature, version))

    # -- artifact builders ----------------------------------------------
    def _notes(self, feature: str, version: str) -> str:
        return (
            f"# {feature} — Release Notes ({version})\n\n"
            "## Features\n- Customer-initiated refunds for eligible orders.\n\n"
            "## Fixes\n- Reject refunds outside the window and on already-refunded orders.\n\n"
            "## Notes\n- Idempotent via `refund_request_id`. Ledger posting is asynchronous.\n"
        )

    def _checklist(self) -> str:
        return (
            "# Deployment Checklist\n\n"
            "1. Run DB migration `V1__refunds.sql` (additive, no downtime).\n"
            "2. Deploy service (blue/green); verify `/health` green.\n"
            "3. Smoke test: eligible refund + rejection paths.\n"
            "4. Confirm outbox publisher draining to the ledger.\n"
        )

    def _rollback(self, version: str) -> str:
        return (
            f"# Rollback Plan ({version})\n\n"
            "- Repoint the router to the previous colour (no data loss; migration is additive).\n"
            "- Refunds are idempotent, so in-flight retries are safe after rollback.\n"
            "- If the ledger already posted, no compensating action is required.\n"
        )

    def _rationale(self, feature: str, version: str) -> str:
        prompt = f"You are a release engineer. In one sentence, summarise releasing '{feature}' {version}."
        try:
            return self.complete([Message(role="user", content=prompt)])
        except Exception:
            return (
                f"Checks green for '{feature}' {version}; release notes, checklist and rollback "
                "prepared — approving the release."
            )
