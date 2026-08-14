"""Backend reads for Completion Batch C: stored-artifact content + webhook-activity feed."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.organisation import Organisation
from app.models.project import Project

pytestmark = pytest.mark.asyncio

_SECRET = "whsec_batch_c"


def _approver() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject='lead-user', persona='lead')}"}


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def _make_project(db: AsyncSession) -> Project:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:8]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    await db.flush()
    project = Project(organisation_id=org.id, name="Refund Service", slug="refund-service")
    db.add(project)
    await db.flush()
    return project


async def test_get_artifact_returns_content(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    pid = str(project.id)
    await client.post(f"/api/v1/projects/{pid}/journey/persist", headers=_approver())

    listed = await client.get(f"/api/v1/projects/{pid}/artifacts")
    artifact_id = listed.json()["items"][0]["id"]

    resp = await client.get(f"/api/v1/projects/{pid}/artifacts/{artifact_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == artifact_id
    assert isinstance(body["content"], str) and len(body["content"]) > 0


async def test_get_artifact_unknown_404(client: AsyncClient, db_session: AsyncSession):
    project = await _make_project(db_session)
    missing = uuid.uuid4()
    resp = await client.get(f"/api/v1/projects/{project.id}/artifacts/{missing}")
    assert resp.status_code == 404


async def test_webhook_events_feed_lists_recent(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", _SECRET)
    body = json.dumps(
        {"action": "opened", "repository": {"full_name": "acme/w"},
         "pull_request": {"number": 1, "title": "x", "state": "open"}}
    ).encode("utf-8")
    await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Delivery": "d-1",
        },
    )
    feed = await client.get("/api/v1/webhooks/events")
    assert feed.status_code == 200
    data = feed.json()
    assert data["total"] == 1
    assert data["items"][0]["source"] == "github"
    assert data["items"][0]["event_type"] == "pull_request"
