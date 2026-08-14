"""Webhook idempotency + Jira project resolution tests (completion Batch B).

Closes the tails of Increments 19/21/22: a redelivered webhook is de-duped (no re-dispatch), and a Jira
event resolves to the owning APEX project by its project key. DB-backed via the aiosqlite fixtures.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.jira import webhooks as jira
from app.models.organisation import Organisation
from app.models.project import Project

# No module-level asyncio mark: the two pure-function tests below are sync; each async test carries its
# own @pytest.mark.asyncio.
_SECRET = "whsec_test_dedup"


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def _seed_project(db: AsyncSession, *, repo: str = "", jira_key: str = "") -> Project:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:8]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    await db.flush()
    project = Project(
        organisation_id=org.id,
        name="Widgets",
        slug="widgets",
        github_repo=repo or None,
        jira_project_key=jira_key or None,
    )
    db.add(project)
    await db.flush()
    return project


# --------------------------------------------------------------------------- pure normalization
def test_jira_parse_event_extracts_project_key() -> None:
    event = jira.parse_event(
        {"webhookEvent": "jira:issue_created", "issue": {"key": "APEX-42", "fields": {}}}
    )
    assert event["project_key"] == "APEX"


def test_jira_parse_event_no_key_yields_none() -> None:
    event = jira.parse_event({"webhookEvent": "jira:issue_created", "issue": {}})
    assert event["project_key"] is None


# --------------------------------------------------------------------------- github idempotency
@pytest.mark.asyncio
async def test_github_duplicate_delivery_is_skipped(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", _SECRET)
    payload = {
        "action": "opened",
        "repository": {"full_name": "acme/widgets"},
        "pull_request": {"number": 3, "title": "x", "state": "open"},
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": _sign(_SECRET, body),
        "X-GitHub-Delivery": "delivery-abc-123",
    }
    first = await client.post("/api/v1/webhooks/github", content=body, headers=headers)
    assert first.status_code == 200
    assert first.json()["duplicate"] is False
    assert first.json()["dispatch"]["phase"] == "development"

    # Same delivery id again → de-duped, no dispatch.
    second = await client.post("/api/v1/webhooks/github", content=body, headers=headers)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["dispatch"] is None


@pytest.mark.asyncio
async def test_github_dedup_falls_back_to_body_hash(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", _SECRET)
    body = json.dumps({"action": "opened", "repository": {"full_name": "acme/w"}}).encode("utf-8")
    headers = {"X-GitHub-Event": "push", "X-Hub-Signature-256": _sign(_SECRET, body)}
    first = await client.post("/api/v1/webhooks/github", content=body, headers=headers)
    second = await client.post("/api/v1/webhooks/github", content=body, headers=headers)
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True  # identical body → same hash → de-duped


# --------------------------------------------------------------------------- jira resolution + dedup
@pytest.mark.asyncio
async def test_jira_resolves_project_and_dedups(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    project = await _seed_project(db_session, jira_key="APEX")
    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {"key": "APEX-7", "fields": {"issuetype": {"name": "Story"}}},
    }
    first = await client.post("/api/v1/webhooks/jira", json=payload)
    assert first.status_code == 200
    body = first.json()
    assert body["duplicate"] is False
    assert body["project"]["id"] == str(project.id)
    assert body["dispatch"]["phase"] == "requirements"

    # Identical payload again → content-hash de-dup.
    second = await client.post("/api/v1/webhooks/jira", json=payload)
    assert second.json()["duplicate"] is True


@pytest.mark.asyncio
async def test_jira_unknown_key_resolves_to_null_project(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    resp = await client.post(
        "/api/v1/webhooks/jira",
        json={"webhookEvent": "jira:issue_created", "issue": {"key": "NOPE-1", "fields": {}}},
    )
    assert resp.status_code == 200
    assert resp.json()["project"] is None
