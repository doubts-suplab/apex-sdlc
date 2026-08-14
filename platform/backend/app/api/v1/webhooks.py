"""Webhook receivers — inbound GitHub + Jira events (Phase 2).

``POST /webhooks/github`` verifies the HMAC-SHA256 signature before parsing (401 on mismatch);
``POST /webhooks/jira`` matches an optional shared secret. Both return the normalized event.
Handlers are intentionally thin — the normalized event is the seam a dispatcher/agent reacts to.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.integrations import dispatch
from app.integrations.github import webhooks as gh
from app.integrations.jira import webhooks as jira
from app.services.project_service import ProjectService
from app.services.webhook_service import WebhookEventService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)


def _bad(status: int, title: str, detail: str) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"type": f"https://apex-sdlc/errors/{title.lower().replace(' ', '-')}",
                "title": title, "status": status, "detail": detail},
    )


def _duplicate(event: dict[str, Any]) -> dict[str, Any]:
    """Response for an already-handled delivery — no dispatch, no side effects."""
    return {"received": True, "duplicate": True, "event": event, "dispatch": None, "project": None}


def _project_ref(project: Any) -> dict[str, str] | None:
    """Compact reference to the resolved APEX project, or None when the event matches no project."""
    if project is None:
        return None
    return {"id": str(project.id), "slug": project.slug, "name": project.name}


@router.post("/github", summary="GitHub webhook receiver (HMAC-SHA256 verified)")
async def github_webhook(
    request: Request,
    x_github_event: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
    x_github_delivery: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    body = await request.body()
    if not gh.verify_signature(get_settings().GITHUB_WEBHOOK_SECRET, body, x_hub_signature_256):
        raise _bad(401, "Invalid Signature", "X-Hub-Signature-256 verification failed.")
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise _bad(400, "Bad Payload", "Webhook body is not valid JSON.") from exc
    event = gh.parse_event(x_github_event or "unknown", payload)
    # Idempotency: skip a delivery already handled (provider retries redeliver the same id/body).
    delivery_id = x_github_delivery or hashlib.sha256(body).hexdigest()
    if not await WebhookEventService(db).record("github", delivery_id, event["event"]):
        return _duplicate(event)
    plan = dispatch.dispatch_for_github(event)
    project = await ProjectService(db).get_by_github_repo(event.get("repo", ""))
    logger.info(
        "webhook.github",
        gh_event=event["event"],
        repo=event.get("repo"),
        dispatch=plan.phase if plan else None,
        project_id=str(project.id) if project else None,
    )
    return {
        "received": True,
        "duplicate": False,
        "event": event,
        "dispatch": plan.to_dict() if plan else None,
        "project": _project_ref(project),
    }


@router.post("/jira", summary="Jira webhook receiver (optional shared-secret)")
async def jira_webhook(
    payload: dict[str, Any],
    secret: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not jira.verify_secret(get_settings().JIRA_WEBHOOK_SECRET, secret):
        raise _bad(401, "Invalid Secret", "Jira webhook shared-secret mismatch.")
    event = jira.parse_event(payload)
    # Jira sends no delivery id, so a canonical content hash de-dupes retried, identical payloads.
    delivery_id = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    if not await WebhookEventService(db).record("jira", delivery_id, event["event"]):
        return _duplicate(event)
    plan = dispatch.dispatch_for_jira(event)
    project = await ProjectService(db).get_by_jira_project_key(event.get("project_key") or "")
    logger.info(
        "webhook.jira",
        jira_event=event["event"],
        issue=event.get("issue_key"),
        dispatch=plan.phase if plan else None,
        project_id=str(project.id) if project else None,
    )
    return {
        "received": True,
        "duplicate": False,
        "event": event,
        "dispatch": plan.to_dict() if plan else None,
        "project": _project_ref(project),
    }
