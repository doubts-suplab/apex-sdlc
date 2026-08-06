"""GitHub webhook verification + event normalization.

Every inbound webhook is authenticated by an HMAC-SHA256 signature (``X-Hub-Signature-256``) before
any processing (platform CLAUDE.md security rule), then normalized into a compact event the platform
reacts to. Pure functions over the raw body + headers — offline-testable, no network.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

HANDLED_EVENTS = ("pull_request", "push", "release", "ping")


def verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    """Constant-time verify ``X-Hub-Signature-256`` (``sha256=<hex>``) against the raw body."""
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header[len("sha256=") :], expected)


def parse_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a GitHub webhook payload into ``{event, action, repo, summary, ...}``."""
    repo = (payload.get("repository") or {}).get("full_name", "")
    base = {"event": event_type, "repo": repo, "action": payload.get("action")}
    if event_type == "pull_request":
        pr = payload.get("pull_request") or {}
        return {
            **base,
            "number": pr.get("number"),
            "title": pr.get("title", ""),
            "state": pr.get("state"),
            "summary": f"PR #{pr.get('number')} {payload.get('action')}: {pr.get('title', '')}",
        }
    if event_type == "push":
        commits = payload.get("commits") or []
        return {
            **base,
            "ref": payload.get("ref"),
            "commit_count": len(commits),
            "summary": f"push to {payload.get('ref')} ({len(commits)} commit(s)) on {repo}",
        }
    if event_type == "release":
        rel = payload.get("release") or {}
        return {
            **base,
            "tag": rel.get("tag_name"),
            "summary": f"release {rel.get('tag_name')} {payload.get('action')} on {repo}",
        }
    return {**base, "summary": f"{event_type} event on {repo}"}
