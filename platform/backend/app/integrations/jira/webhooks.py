"""Jira webhook event normalization.

Jira webhooks carry a ``webhookEvent`` discriminator (e.g. ``jira:issue_created``). Jira does not
sign payloads, so authenticity is an optional shared secret matched against a query token. Pure
functions — offline-testable.
"""

from __future__ import annotations

import hmac
from typing import Any


def verify_secret(configured: str, provided: str | None) -> bool:
    """Constant-time compare an optional shared secret (empty configured → accept, dev mode)."""
    if not configured:
        return True
    return bool(provided) and hmac.compare_digest(configured, provided or "")


def parse_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Jira webhook payload into ``{event, issue_key, summary, ...}``."""
    event = payload.get("webhookEvent", "unknown")
    issue = payload.get("issue") or {}
    fields = issue.get("fields") or {}
    key = issue.get("key")
    # Project key = the issue-key prefix ("APEX" in "APEX-42"); resolves the owning APEX project.
    project_key = key.split("-", 1)[0] if key and "-" in key else None
    return {
        "event": event,
        "issue_key": key,
        "project_key": project_key,
        "issue_type": (fields.get("issuetype") or {}).get("name"),
        "status": (fields.get("status") or {}).get("name"),
        "summary": f"{event}: {key or '(no issue)'} — {fields.get('summary', '')}".strip(),
    }
