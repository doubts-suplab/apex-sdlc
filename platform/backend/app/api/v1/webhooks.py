"""Webhook receivers — inbound GitHub + Jira events (Phase 2).

``POST /webhooks/github`` verifies the HMAC-SHA256 signature before parsing (401 on mismatch);
``POST /webhooks/jira`` matches an optional shared secret. Both return the normalized event.
Handlers are intentionally thin — the normalized event is the seam a dispatcher/agent reacts to.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.github import webhooks as gh
from app.integrations.jira import webhooks as jira

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)


def _bad(status: int, title: str, detail: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"type": f"https://apex-sdlc/errors/{title.lower().replace(' ', '-')}",
                "title": title, "status": status, "detail": detail},
    )


@router.post("/github", summary="GitHub webhook receiver (HMAC-SHA256 verified)")
async def github_webhook(
    request: Request,
    x_github_event: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    body = await request.body()
    if not gh.verify_signature(get_settings().GITHUB_WEBHOOK_SECRET, body, x_hub_signature_256):
        raise _bad(401, "Invalid Signature", "X-Hub-Signature-256 verification failed.")
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise _bad(400, "Bad Payload", "Webhook body is not valid JSON.") from exc
    event = gh.parse_event(x_github_event or "unknown", payload)
    logger.info("webhook.github", gh_event=event["event"], repo=event.get("repo"))
    return {"received": True, "event": event}


@router.post("/jira", summary="Jira webhook receiver (optional shared-secret)")
async def jira_webhook(
    payload: dict[str, Any],
    secret: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    if not jira.verify_secret(get_settings().JIRA_WEBHOOK_SECRET, secret):
        raise _bad(401, "Invalid Secret", "Jira webhook shared-secret mismatch.")
    event = jira.parse_event(payload)
    logger.info("webhook.jira", jira_event=event["event"], issue=event.get("issue_key"))
    return {"received": True, "event": event}
