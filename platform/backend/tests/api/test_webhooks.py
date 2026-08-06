"""Webhook receiver tests — GitHub HMAC verification + GitHub/Jira event normalization.

Fully offline: signatures are computed in-process, no network. Exercises the security rule
(reject unsigned/mismatched GitHub webhooks with 401) and the normalized-event contract both
endpoints return.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github import webhooks as gh
from app.integrations.jira import webhooks as jira
from app.models.organisation import Organisation
from app.models.project import Project

_SECRET = "whsec_test_1234567890"


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


# --------------------------------------------------------------------------- pure functions


def test_verify_signature_accepts_valid() -> None:
    body = b'{"hello": "world"}'
    assert gh.verify_signature(_SECRET, body, _sign(_SECRET, body)) is True


def test_verify_signature_rejects_tampered_body() -> None:
    sig = _sign(_SECRET, b'{"hello": "world"}')
    assert gh.verify_signature(_SECRET, b'{"hello": "evil"}', sig) is False


def test_verify_signature_rejects_missing_or_malformed_header() -> None:
    body = b"{}"
    assert gh.verify_signature(_SECRET, body, None) is False
    assert gh.verify_signature(_SECRET, body, "md5=abc") is False
    # Empty configured secret never auto-accepts a signed GitHub webhook.
    assert gh.verify_signature("", body, _sign(_SECRET, body)) is False


def test_parse_pull_request_event() -> None:
    payload = {
        "action": "opened",
        "repository": {"full_name": "acme/widgets"},
        "pull_request": {"number": 7, "title": "Add gate", "state": "open"},
    }
    event = gh.parse_event("pull_request", payload)
    assert event["event"] == "pull_request"
    assert event["repo"] == "acme/widgets"
    assert event["number"] == 7
    assert event["summary"] == "PR #7 opened: Add gate"


def test_parse_push_event() -> None:
    payload = {
        "ref": "refs/heads/main",
        "repository": {"full_name": "acme/widgets"},
        "commits": [{"id": "a"}, {"id": "b"}],
    }
    event = gh.parse_event("push", payload)
    assert event["commit_count"] == 2
    assert event["ref"] == "refs/heads/main"
    assert "2 commit(s)" in event["summary"]


def test_parse_release_event() -> None:
    payload = {
        "action": "published",
        "repository": {"full_name": "acme/widgets"},
        "release": {"tag_name": "v1.2.0"},
    }
    event = gh.parse_event("release", payload)
    assert event["tag"] == "v1.2.0"
    assert event["summary"] == "release v1.2.0 published on acme/widgets"


def test_jira_verify_secret_dev_mode_and_mismatch() -> None:
    # Empty configured secret → accept (dev mode).
    assert jira.verify_secret("", None) is True
    # Configured secret must match.
    assert jira.verify_secret(_SECRET, _SECRET) is True
    assert jira.verify_secret(_SECRET, "nope") is False
    assert jira.verify_secret(_SECRET, None) is False


def test_jira_parse_event() -> None:
    payload = {
        "webhookEvent": "jira:issue_created",
        "issue": {
            "key": "APEX-42",
            "fields": {
                "summary": "Wire the spine",
                "issuetype": {"name": "Story"},
                "status": {"name": "To Do"},
            },
        },
    }
    event = jira.parse_event(payload)
    assert event["event"] == "jira:issue_created"
    assert event["issue_key"] == "APEX-42"
    assert event["issue_type"] == "Story"
    assert event["status"] == "To Do"
    assert "APEX-42" in event["summary"]


# --------------------------------------------------------------------------- endpoints


@pytest.mark.asyncio
async def test_github_webhook_accepts_valid_signature(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", _SECRET)
    payload = {
        "action": "opened",
        "repository": {"full_name": "acme/widgets"},
        "pull_request": {"number": 3, "title": "Feature", "state": "open"},
    }
    body = json.dumps(payload).encode("utf-8")
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": _sign(_SECRET, body),
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] is True
    assert data["event"]["event"] == "pull_request"
    assert data["event"]["repo"] == "acme/widgets"
    # A PR-opened event routes to the Development phase (PR review).
    assert data["dispatch"]["phase"] == "development"


@pytest.mark.asyncio
async def test_github_webhook_rejects_invalid_signature(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", _SECRET)
    body = json.dumps({"action": "opened"}).encode("utf-8")
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=deadbeef",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["title"] == "Invalid Signature"


@pytest.mark.asyncio
async def test_jira_webhook_accepts_and_parses(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JIRA_WEBHOOK_SECRET", _SECRET)
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {"key": "APEX-1", "fields": {"summary": "x"}},
    }
    resp = await client.post(f"/api/v1/webhooks/jira?secret={_SECRET}", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["event"]["issue_key"] == "APEX-1"


@pytest.mark.asyncio
async def test_jira_webhook_rejects_secret_mismatch(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JIRA_WEBHOOK_SECRET", _SECRET)
    resp = await client.post(
        "/api/v1/webhooks/jira?secret=wrong",
        json={"webhookEvent": "jira:issue_created"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["title"] == "Invalid Secret"


# --------------------------------------------------------------------------- project resolution


async def _seed_project(db: AsyncSession, repo: str) -> Project:
    org = Organisation(name=f"Org {uuid.uuid4().hex[:8]}", slug=f"org-{uuid.uuid4().hex[:8]}")
    db.add(org)
    await db.flush()
    project = Project(
        organisation_id=org.id, name="Widgets", slug="widgets", github_repo=repo
    )
    db.add(project)
    await db.flush()
    return project


@pytest.mark.asyncio
async def test_github_webhook_resolves_owning_project(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", _SECRET)
    project = await _seed_project(db_session, "acme/widgets")
    payload = {
        "action": "opened",
        "repository": {"full_name": "acme/widgets"},
        "pull_request": {"number": 5, "title": "Fix", "state": "open"},
    }
    body = json.dumps(payload).encode("utf-8")
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": _sign(_SECRET, body),
        },
    )
    assert resp.status_code == 200
    ref = resp.json()["project"]
    assert ref is not None
    assert ref["id"] == str(project.id)
    assert ref["slug"] == "widgets"


@pytest.mark.asyncio
async def test_github_webhook_resolves_project_case_insensitively(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", _SECRET)
    await _seed_project(db_session, "Acme/Widgets")
    payload = {
        "action": "published",
        "repository": {"full_name": "acme/widgets"},
        "release": {"tag_name": "v2.0.0"},
    }
    body = json.dumps(payload).encode("utf-8")
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "release",
            "X-Hub-Signature-256": _sign(_SECRET, body),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["project"]["slug"] == "widgets"


@pytest.mark.asyncio
async def test_github_webhook_unknown_repo_resolves_to_null_project(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", _SECRET)
    payload = {
        "action": "opened",
        "repository": {"full_name": "nobody/unknown"},
        "pull_request": {"number": 1, "title": "x", "state": "open"},
    }
    body = json.dumps(payload).encode("utf-8")
    resp = await client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": _sign(_SECRET, body),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["project"] is None
