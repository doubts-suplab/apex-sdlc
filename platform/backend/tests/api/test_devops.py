"""DevOps flow API tests — RBAC + the governed flow over HTTP."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token

pytestmark = pytest.mark.asyncio

_TARGETS = {
    "feature": "Refund retry fix",
    "repo": "acme/refund-service",
    "jira_project_key": "REF",
    "confluence_space": "REF",
    "slack_channel": "#refunds",
    "jenkins_job": "refund-service-ci",
}


def _auth(persona: str = "lead") -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject='u', persona=persona)}"}


async def test_flow_requires_auth(client: AsyncClient):
    resp = await client.post("/api/v1/devops/flow", json={"intent": "open a PR", "context": {}})
    assert resp.status_code == 401


async def test_flow_forbids_non_approver(client: AsyncClient):
    resp = await client.post(
        "/api/v1/devops/flow",
        json={"intent": "open a PR", "context": {}},
        headers=_auth("qa"),  # qa is not an approver for this action
    )
    assert resp.status_code == 403


async def test_flow_executes_full_pipeline(client: AsyncClient):
    resp = await client.post(
        "/api/v1/devops/flow",
        json={
            "intent": "ship the PR, run the build, file a story, publish docs, tell the team",
            "context": _TARGETS,
        },
        headers=_auth("lead"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "ALLOW"
    assert body["executed"] is True
    assert body["auto_enforced"] is True


async def test_flow_holds_underspecified_for_review(client: AsyncClient):
    resp = await client.post(
        "/api/v1/devops/flow",
        json={"intent": "open a PR and notify the team", "context": {}},
        headers=_auth("lead"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "SUGGEST"
    assert body["executed"] is False
