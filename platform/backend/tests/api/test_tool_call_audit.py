"""Per-tool-call audit tests — the DevOps flow records each executed governed call."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.devops import run_devops_flow
from app.integrations.llm.stub_provider import StubLLMProvider

pytestmark = pytest.mark.asyncio

_TARGETS = {
    "feature": "Refund retry fix",
    "repo": "acme/refund-service",
    "jira_project_key": "REF",
    "confluence_space": "REF",
    "slack_channel": "#refunds",
    "jenkins_job": "refund-service-ci",
}
_INTENT = "ship the PR, run the build, file a story, publish docs, tell the team"


def _auth(persona: str = "lead") -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=f'{persona}-user', persona=persona)}"}


async def test_flow_result_carries_executed_tool_calls():
    result = run_devops_flow(llm=StubLLMProvider(), intent=_INTENT, context=_TARGETS)
    assert result.decision.action.name == "ALLOW"
    assert len(result.tool_calls) == 5
    assert result.tool_calls[0]["result"]["system"] == "github"


async def test_devops_flow_api_persists_tool_call_audit(client: AsyncClient):
    resp = await client.post(
        "/api/v1/devops/flow",
        headers=_auth("lead"),
        json={"intent": _INTENT, "context": _TARGETS},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["executed"] is True
    assert body["tool_calls"] == 5

    audit = await client.get("/api/v1/devops/tool-calls")
    assert audit.status_code == 200
    data = audit.json()
    assert data["total"] == 5
    systems = {row["system"] for row in data["items"]}
    assert "github" in systems and "jira" in systems
    assert all(row["actor"] == "lead-user" for row in data["items"])


async def test_devops_flow_dry_run_records_nothing(client: AsyncClient):
    # An under-specified intent (no concrete targets) is proposed, not executed → no audit rows.
    resp = await client.post(
        "/api/v1/devops/flow",
        headers=_auth("lead"),
        json={"intent": "open a PR", "context": {}},
    )
    assert resp.status_code == 200
    assert resp.json()["executed"] is False
    audit = await client.get("/api/v1/devops/tool-calls")
    assert audit.json()["total"] == 0
