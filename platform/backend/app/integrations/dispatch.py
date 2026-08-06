"""Inbound event → phase-agent dispatch routing.

A normalized webhook event (from ``integrations/github/webhooks.py`` or
``integrations/jira/webhooks.py``) is mapped here to the SDLC phase whose agent should react — a
``pull_request`` opened → Development (PR Reviewer), a ``release`` published → CI/CD (Release
Engineer), a new Jira Story → Requirements (BA). This is the seam a background dispatcher consumes
to enqueue an agent run.

Like the DevOps intent planner, this only **proposes** a reaction — it has no authority of its own.
Whether the proposed agent may auto-enforce is still decided by the harness confidence gate at run
time, and the tool registry (default-deny) still governs any side effect. Pure, deterministic,
offline-testable — the mapping is transparent so the routing decision is auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agents.catalog import spec_for

# GitHub pull_request actions worth a review pass. Housekeeping (labeled, assigned, …) is noise.
_PR_ACTIONS = frozenset({"opened", "reopened", "synchronize", "ready_for_review", "edited"})
# Jira webhookEvents that introduce or change a story worth (re)analysing.
_JIRA_STORY_EVENTS = frozenset({"jira:issue_created", "jira:issue_updated"})
_STORY_TYPES = frozenset({"Story", "Epic", "Task"})


@dataclass(frozen=True)
class WebhookDispatch:
    """A proposed reaction to an inbound event: which phase-agent should run, and why.

    ``phase`` / ``agent`` / ``persona`` come straight from the phase catalog so this can never name
    an agent the platform does not run. ``reason`` is the human-readable audit line.
    """

    phase: str
    agent: str
    persona: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "phase": self.phase,
            "agent": self.agent,
            "persona": self.persona,
            "reason": self.reason,
        }


def _for_phase(phase: str, reason: str) -> WebhookDispatch:
    spec = spec_for(phase)
    return WebhookDispatch(
        phase=spec.phase,
        agent=spec.agent_name,
        persona=spec.primary_persona,
        reason=reason,
    )


def dispatch_for_github(event: dict[str, Any]) -> WebhookDispatch | None:
    """Route a normalized GitHub event to a phase-agent, or ``None`` when nothing should react."""
    kind = event.get("event")
    action = event.get("action")
    if kind == "pull_request" and action in _PR_ACTIONS:
        number = event.get("number")
        return _for_phase(
            "development",
            f"PR #{number} {action} on {event.get('repo')} → PR review (advisory).",
        )
    if kind == "release" and action == "published":
        return _for_phase(
            "cicd",
            f"release {event.get('tag')} published on {event.get('repo')} → release artifacts.",
        )
    return None


def dispatch_for_jira(event: dict[str, Any]) -> WebhookDispatch | None:
    """Route a normalized Jira event to a phase-agent, or ``None`` when nothing should react."""
    if event.get("event") in _JIRA_STORY_EVENTS and event.get("issue_type") in _STORY_TYPES:
        return _for_phase(
            "requirements",
            f"{event.get('issue_type')} {event.get('issue_key')} changed → requirements refresh.",
        )
    return None
