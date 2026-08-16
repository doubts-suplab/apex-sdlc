"""Generic manifest/org ingestion — API-level tests.

The eeik engine used by the request-scoped service is patched to a deterministic fake so these tests are
hermetic (pass with or without the real ``eeik`` package installed).
"""

from __future__ import annotations

import pytest
import yaml
from httpx import AsyncClient

VALID_MANIFEST = {
    "schema_version": "1.0",
    "project": {
        "name": "acme-core",
        "description": "Core.",
        "owner": "acme",
        "domain": "generic",
        "project_type": "greenfield",
    },
    "technology": {"backend": {"language": "java", "version": 21, "framework": "spring-boot"}},
    "architecture": {"style": "modular-monolith", "patterns": ["ddd"], "api_style": "rest"},
    "cloud": {"provider": "aws", "infra_as_code": "cdk", "multi_account": True},
    "governance": {
        "profile": "enterprise",
        "reviews_required": ["architecture-review"],
        "compliance_frameworks": ["gdpr"],
        "adr_required": True,
        "coverage_threshold": 80,
    },
    "delivery": {
        "model": "single-team",
        "methodology": "incremental",
        "sprint_length_weeks": 2,
        "cicd_platform": "github-actions",
    },
}

_REQUIRED = ("technology", "architecture", "cloud", "governance", "delivery")


class _FakeEngine:
    mode = "sdk"

    def validate(self, manifest: dict) -> dict:
        missing = [k for k in _REQUIRED if k not in manifest]
        return {"valid": not missing, "errors": [f"missing '{k}'" for k in missing], "warnings": []}

    def resolve_packs(self, manifest: dict) -> list[str]:
        return ["core", "governance"]

    def catalog(self, tag: str | None = None) -> list[dict]:
        return []

    def verify(self) -> dict:
        return {"ok": True}


@pytest.fixture(autouse=True)
def _fake_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    # The request-scoped ManifestIngestService resolves its engine via this symbol.
    monkeypatch.setattr("app.onboarding.ingest.get_engine", lambda mode=None: _FakeEngine())


async def _org(client: AsyncClient, slug: str) -> str:
    r = await client.post("/api/v1/organisations/", json={"name": f"Org {slug}", "slug": slug})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def _project(client: AsyncClient, org_id: str, slug: str, repo: str) -> str:
    r = await client.post(
        "/api/v1/projects/",
        json={"organisation_id": org_id, "name": slug, "slug": slug, "github_repo": repo},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


@pytest.mark.asyncio
async def test_post_then_get_project_manifest(client: AsyncClient) -> None:
    org = await _org(client, "acme")
    pid = await _project(client, org, "acme-core", "acme/acme-core")

    r = await client.post(
        f"/api/v1/projects/{pid}/manifest", json={"manifest": VALID_MANIFEST, "source_ref": "test"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["governance_profile"] == "enterprise"
    assert body["coverage_threshold"] == 80
    assert body["compliance_frameworks"] == ["gdpr"]
    assert body["resolved_packs"] == ["core", "governance"]
    assert body["engine"] == "sdk"

    g = await client.get(f"/api/v1/projects/{pid}/manifest")
    assert g.status_code == 200
    assert g.json()["governance_profile"] == "enterprise"


@pytest.mark.asyncio
async def test_get_manifest_404_when_none(client: AsyncClient) -> None:
    org = await _org(client, "acme2")
    pid = await _project(client, org, "acme-x", "acme/acme-x")
    g = await client.get(f"/api/v1/projects/{pid}/manifest")
    assert g.status_code == 404
    assert g.json()["status"] == 404  # RFC 7807


@pytest.mark.asyncio
async def test_post_manifest_unknown_project_404(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/manifest",
        json={"manifest": VALID_MANIFEST},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_post_invalid_manifest_422(client: AsyncClient) -> None:
    org = await _org(client, "acme3")
    pid = await _project(client, org, "acme-y", "acme/acme-y")
    r = await client.post(
        f"/api/v1/projects/{pid}/manifest",
        json={"manifest": {"schema_version": "1.0", "project": {"name": "x"}}},
    )
    assert r.status_code == 422, r.text
    assert r.json()["status"] == 422


@pytest.mark.asyncio
async def test_ingest_org_requires_workspace_root_400(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/ingest/organisation",
        json={"descriptor": {"organisation": {"slug": "z", "name": "Z"}, "projects": []}},
    )
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_ingest_org_from_local_workspace(client: AsyncClient, tmp_path) -> None:
    # Lay out a local workspace: <root>/acme-core/project-manifest.yaml
    (tmp_path / "acme-core").mkdir()
    (tmp_path / "acme-core" / "project-manifest.yaml").write_text(yaml.safe_dump(VALID_MANIFEST))

    descriptor = {
        "organisation": {"name": "Acme WS", "slug": "acme-ws"},
        "projects": [
            {
                "name": "Core",
                "slug": "acme-core",
                "github_repo": "acme/acme-core",
                "manifest_path": "project-manifest.yaml",
            }
        ],
    }
    r = await client.post(
        "/api/v1/ingest/organisation",
        json={"descriptor": descriptor, "workspace_root": str(tmp_path)},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["organisation_slug"] == "acme-ws"
    assert [p["slug"] for p in body["projects"]] == ["acme-core"]
    assert body["skipped"] == []
