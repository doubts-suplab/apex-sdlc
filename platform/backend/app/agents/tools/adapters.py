"""Offline, deterministic tool adapters.

Each adapter is a ``dict -> dict`` callable matching the harness ``ToolImpl`` shape. They perform **no
network I/O**: they validate the required arguments and return a structured, reproducible result payload
that stands in for the real system's response (a PR URL, a Jira key, a build number…). This is what makes
the whole DevOps flow verifiable offline and keeps ``examples/`` byte-stable.

To go live, register a **credentialed adapter** with the same name and signature instead — e.g. one that
wraps ``app.integrations.github.client.GitHubClient`` — and nothing above the registry changes. The
determinism here (hash-derived ids) is a stand-in, not a promise about the real system's ids.
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.agents.tools.catalog import TOOLS_BY_NAME


class ToolArgumentError(ValueError):
    """Raised when a tool is invoked without its catalog-required arguments."""


def _require(tool_name: str, args: dict[str, Any]) -> None:
    spec = TOOLS_BY_NAME[tool_name]
    missing = [k for k in spec.required_args if not args.get(k)]
    if missing:
        raise ToolArgumentError(f"{tool_name} missing required argument(s): {', '.join(missing)}")


def _stable_id(*parts: str, mod: int) -> int:
    """A deterministic small integer derived from the arguments (stands in for a real id)."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % mod + 1


def open_pull_request(args: dict[str, Any]) -> dict[str, Any]:
    _require("github.open_pull_request", args)
    repo, title = args["repo"], args["title"]
    number = _stable_id(repo, title, args["head"], args["base"], mod=9000)
    return {
        "system": "github",
        "action": "open_pull_request",
        "number": number,
        "url": f"https://github.com/{repo}/pull/{number}",
        "title": title,
        "state": "open",
    }


def create_issue(args: dict[str, Any]) -> dict[str, Any]:
    _require("jira.create_issue", args)
    key = args["project_key"]
    number = _stable_id(key, args["summary"], args["issue_type"], mod=9000)
    return {
        "system": "jira",
        "action": "create_issue",
        "key": f"{key}-{number}",
        "issue_type": args["issue_type"],
        "summary": args["summary"],
        "status": "To Do",
    }


def publish_page(args: dict[str, Any]) -> dict[str, Any]:
    _require("confluence.publish_page", args)
    space, title = args["space_key"], args["title"]
    page_id = _stable_id(space, title, mod=900000)
    return {
        "system": "confluence",
        "action": "publish_page",
        "page_id": page_id,
        "url": f"https://confluence.example.com/spaces/{space}/pages/{page_id}",
        "title": title,
    }


def post_message(args: dict[str, Any]) -> dict[str, Any]:
    _require("slack.post_message", args)
    channel = args["channel"]
    ts = _stable_id(channel, args["text"], mod=1_000_000)
    return {
        "system": "slack",
        "action": "post_message",
        "channel": channel,
        "ts": f"171{ts:06d}.000100",
        "delivered": True,
    }


def trigger_build(args: dict[str, Any]) -> dict[str, Any]:
    _require("jenkins.trigger_build", args)
    job = args["job"]
    build_number = _stable_id(job, str(args.get("parameters", "")), mod=5000)
    return {
        "system": "jenkins",
        "action": "trigger_build",
        "job": job,
        "build_number": build_number,
        "url": f"https://jenkins.example.com/job/{job}/{build_number}/",
        "queued": True,
    }


# Name → offline adapter. A live build swaps these for credentialed adapters of the same shape.
OFFLINE_ADAPTERS: dict[str, Any] = {
    "github.open_pull_request": open_pull_request,
    "jira.create_issue": create_issue,
    "confluence.publish_page": publish_page,
    "slack.post_message": post_message,
    "jenkins.trigger_build": trigger_build,
}
