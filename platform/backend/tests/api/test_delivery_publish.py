from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func, select

from app.api.deps import get_github_client
from app.db.session import get_db
from app.main import create_app
from app.models.audit import AuditLog


class FakeGitHubClient:
    """Records issue creations and returns a canned issue — no network."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create_issue(
        self, repo: str, title: str, body: str = "", labels: list[str] | None = None
    ) -> dict[str, Any]:
        self.calls.append({"repo": repo, "title": title, "body": body, "labels": labels})
        number = len(self.calls)
        return {
            "number": number,
            "html_url": f"https://github.com/{repo}/issues/{number}",
            "state": "open",
        }


@pytest_asyncio.fixture()
async def fake_github() -> FakeGitHubClient:
    return FakeGitHubClient()


@pytest_asyncio.fixture()
async def gh_client(
    db_session: AsyncSession, fake_github: FakeGitHubClient
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with the DB and GitHub client dependencies overridden (offline)."""
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_github_client] = lambda: fake_github

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _project_with_repo(client: AsyncClient, repo: str | None) -> str:
    org = await client.post(
        "/api/v1/organisations/", json={"name": "Pub Org", "slug": "pub-org"}
    )
    org_id = org.json()["id"]
    body: dict[str, Any] = {"organisation_id": org_id, "name": "Pub Svc", "slug": "pub-svc"}
    if repo is not None:
        body["github_repo"] = repo
    proj = await client.post("/api/v1/projects/", json=body)
    assert proj.status_code == 201, proj.text
    return str(proj.json()["id"])


async def _add_delivery(client: AsyncClient, project_id: str, **body: Any) -> str:
    resp = await client.post(f"/api/v1/projects/{project_id}/deliveries/", json=body)
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


@pytest.mark.asyncio
async def test_publish_creates_issue_and_marks_planned(
    gh_client: AsyncClient, fake_github: FakeGitHubClient
) -> None:
    project_id = await _project_with_repo(gh_client, "doubts-suplab/aether-flow")
    delivery_id = await _add_delivery(
        gh_client, project_id, title="Ship business-hours SLAs", priority="high", estimate_points=5
    )

    resp = await gh_client.post(
        f"/api/v1/projects/{project_id}/deliveries/{delivery_id}/publish"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["issue_number"] == 1
    assert body["issue_url"] == "https://github.com/doubts-suplab/aether-flow/issues/1"
    # delivery advanced to planned and now carries the issue URL
    assert body["delivery"]["status"] == "planned"
    assert body["delivery"]["target_ref"] == body["issue_url"]

    # the issue was created with the delivery title + apex label
    assert len(fake_github.calls) == 1
    call = fake_github.calls[0]
    assert call["repo"] == "doubts-suplab/aether-flow"
    assert call["title"] == "Ship business-hours SLAs"
    assert call["labels"] == ["apex-delivery"]
    assert delivery_id in call["body"]  # apex delivery id embedded for traceability


@pytest.mark.asyncio
async def test_publish_writes_audit_row(
    gh_client: AsyncClient, db_session
) -> None:
    project_id = await _project_with_repo(gh_client, "doubts-suplab/aether-core")
    delivery_id = await _add_delivery(gh_client, project_id, title="Audited delivery")

    resp = await gh_client.post(
        f"/api/v1/projects/{project_id}/deliveries/{delivery_id}/publish"
    )
    assert resp.status_code == 200, resp.text

    # An append-only audit entry records the governed write-back.
    count = await db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.agent_name == "delivery-publish")
    )
    assert count == 1
    row = await db_session.scalar(
        select(AuditLog).where(AuditLog.agent_name == "delivery-publish")
    )
    assert row.action == "ALLOW"
    assert row.auto_enforced is False
    assert "doubts-suplab/aether-core" in row.summary


@pytest.mark.asyncio
async def test_publish_without_repo_is_conflict(
    gh_client: AsyncClient, fake_github: FakeGitHubClient
) -> None:
    project_id = await _project_with_repo(gh_client, None)  # no github_repo
    delivery_id = await _add_delivery(gh_client, project_id, title="orphan")

    resp = await gh_client.post(
        f"/api/v1/projects/{project_id}/deliveries/{delivery_id}/publish"
    )
    assert resp.status_code == 409
    assert resp.json()["status"] == 409  # RFC 7807
    assert fake_github.calls == []  # never reached GitHub


@pytest.mark.asyncio
async def test_double_publish_is_conflict(
    gh_client: AsyncClient, fake_github: FakeGitHubClient
) -> None:
    project_id = await _project_with_repo(gh_client, "doubts-suplab/aether")
    delivery_id = await _add_delivery(gh_client, project_id, title="once")

    first = await gh_client.post(
        f"/api/v1/projects/{project_id}/deliveries/{delivery_id}/publish"
    )
    assert first.status_code == 200
    second = await gh_client.post(
        f"/api/v1/projects/{project_id}/deliveries/{delivery_id}/publish"
    )
    assert second.status_code == 409
    assert len(fake_github.calls) == 1  # not published twice


@pytest.mark.asyncio
async def test_publish_unknown_delivery_is_404(gh_client: AsyncClient) -> None:
    project_id = await _project_with_repo(gh_client, "doubts-suplab/aether")
    resp = await gh_client.post(
        f"/api/v1/projects/{project_id}/deliveries/00000000-0000-0000-0000-000000000000/publish"
    )
    assert resp.status_code == 404
