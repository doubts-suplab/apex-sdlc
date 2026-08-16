"""Generic manifest/org ingestion — service-level tests.

Uses an injected fake eeik engine so the flow is deterministic and hermetic (independent of whether the
real ``eeik`` package is installed). Nothing here names any real organisation — the org is data.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organisation import Organisation
from app.models.project import Project
from app.models.project_manifest import ProjectManifestRecord
from app.onboarding.ingest import ManifestIngestService
from app.onboarding.resolver import ManifestNotFoundError
from app.onboarding.service import ManifestInvalidError

# A manifest shaped like the canonical eeik schema. The fake engine validates on required top-level keys.
VALID_MANIFEST = {
    "schema_version": "1.0",
    "project": {
        "name": "acme-billing",
        "description": "Billing service.",
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


class FakeEngine:
    """A deterministic stand-in for the eeik engine — validity keyed on required top-level sections."""

    mode = "sdk"

    def __init__(self, packs: list[str] | None = None, force_invalid: bool = False) -> None:
        self._packs = packs or ["core", "governance"]
        self._force_invalid = force_invalid

    def validate(self, manifest: dict) -> dict:
        missing = [k for k in _REQUIRED if k not in manifest]
        valid = not missing and not self._force_invalid
        errors = [f"missing '{k}'" for k in missing] or (["rejected"] if self._force_invalid else [])
        return {"valid": valid, "errors": errors, "warnings": []}

    def resolve_packs(self, manifest: dict) -> list[str]:
        return list(self._packs)

    def catalog(self, tag: str | None = None) -> list[dict]:
        return []

    def verify(self) -> dict:
        return {"ok": True}


class FakeResolver:
    """Serves manifests from an in-memory ``{github_repo: manifest}`` map."""

    def __init__(self, manifests: dict[str, dict]) -> None:
        self._manifests = manifests

    def fetch(self, github_repo: str, manifest_path: str) -> tuple[dict, str]:
        if github_repo not in self._manifests:
            raise ManifestNotFoundError(f"no manifest for {github_repo}")
        return self._manifests[github_repo], f"fake://{github_repo}/{manifest_path}"


async def _org(db: AsyncSession, slug: str = "acme") -> Organisation:
    org = Organisation(name=slug.title(), slug=slug)
    db.add(org)
    await db.flush()
    return org


async def _project(db: AsyncSession, org: Organisation, slug: str, repo: str) -> Project:
    proj = Project(organisation_id=org.id, name=slug, slug=slug, github_repo=repo)
    db.add(proj)
    await db.flush()
    return proj


@pytest.mark.asyncio
async def test_attach_manifest_persists_posture_and_raw_fidelity(db_session: AsyncSession) -> None:
    org = await _org(db_session)
    proj = await _project(db_session, org, "acme-billing", "acme/acme-billing")
    svc = ManifestIngestService(db_session, engine=FakeEngine(packs=["core", "java", "governance"]))

    rec = await svc.attach_manifest(proj, manifest=VALID_MANIFEST, source_ref="unit")

    assert rec.governance_profile == "enterprise"
    # coverage_threshold survives even though APEX's internal Pydantic GovernanceSpec drops it —
    # ingestion persists from the raw manifest dict.
    assert rec.coverage_threshold == 80
    assert rec.raw["governance"]["coverage_threshold"] == 80
    assert rec.compliance_frameworks == ["gdpr"]
    assert rec.resolved_packs == ["core", "java", "governance"]
    assert rec.engine == "sdk"
    assert rec.source_ref == "unit"


@pytest.mark.asyncio
async def test_attach_manifest_is_idempotent(db_session: AsyncSession) -> None:
    org = await _org(db_session)
    proj = await _project(db_session, org, "acme-billing", "acme/acme-billing")

    await ManifestIngestService(db_session, engine=FakeEngine(packs=["core"])).attach_manifest(
        proj, manifest=VALID_MANIFEST
    )
    rec = await ManifestIngestService(
        db_session, engine=FakeEngine(packs=["core", "java"])
    ).attach_manifest(proj, manifest=VALID_MANIFEST)

    count = (
        await db_session.execute(
            select(func.count())
            .select_from(ProjectManifestRecord)
            .where(ProjectManifestRecord.project_id == proj.id)
        )
    ).scalar_one()
    assert count == 1  # refreshed in place, not duplicated
    assert rec.resolved_packs == ["core", "java"]


@pytest.mark.asyncio
async def test_attach_manifest_invalid_raises(db_session: AsyncSession) -> None:
    org = await _org(db_session)
    proj = await _project(db_session, org, "acme-x", "acme/acme-x")
    svc = ManifestIngestService(db_session, engine=FakeEngine(force_invalid=True))

    with pytest.raises(ManifestInvalidError):
        await svc.attach_manifest(proj, manifest=VALID_MANIFEST)


@pytest.mark.asyncio
async def test_attach_manifest_vendored_when_no_engine(db_session: AsyncSession) -> None:
    org = await _org(db_session)
    proj = await _project(db_session, org, "acme-y", "acme/acme-y")
    svc = ManifestIngestService(db_session, engine=FakeEngine())
    svc._engine = None  # simulate eeik not installed → vendored offline path

    rec = await svc.attach_manifest(proj, manifest=VALID_MANIFEST)

    assert rec.engine == "vendored"
    assert rec.resolved_packs == []  # no engine to resolve packs
    assert rec.governance_profile == "enterprise"  # posture still persisted from the raw manifest


@pytest.mark.asyncio
async def test_ingest_org_creates_then_idempotent(db_session: AsyncSession) -> None:
    descriptor = {
        "organisation": {"name": "Acme", "slug": "acme", "description": "example"},
        "projects": [
            {"name": "Billing", "slug": "acme-billing", "github_repo": "acme/acme-billing"},
            {"name": "Portal", "slug": "acme-portal", "github_repo": "acme/acme-portal"},
        ],
    }
    manifests = {"acme/acme-billing": VALID_MANIFEST, "acme/acme-portal": VALID_MANIFEST}

    r1 = await ManifestIngestService(db_session, engine=FakeEngine()).ingest_org(
        descriptor, FakeResolver(manifests)
    )
    assert {p.slug for p in r1.projects} == {"acme-billing", "acme-portal"}
    assert all(p.created for p in r1.projects)

    r2 = await ManifestIngestService(db_session, engine=FakeEngine()).ingest_org(
        descriptor, FakeResolver(manifests)
    )
    assert all(not p.created for p in r2.projects)  # found, not recreated

    total = (
        await db_session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.organisation_id == uuid.UUID(r2.organisation_id))
        )
    ).scalar_one()
    assert total == 2  # no duplicates


@pytest.mark.asyncio
async def test_seed_from_descriptor_reads_files_and_ingests(db_session: AsyncSession, tmp_path) -> None:
    import yaml

    from app.seeds.from_descriptor import seed_from_descriptor

    # Local workspace: <root>/<repo-basename>/project-manifest.yaml (owner-agnostic layout).
    for name in ("acme-billing", "acme-portal"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "project-manifest.yaml").write_text(yaml.safe_dump(VALID_MANIFEST))

    descriptor_path = tmp_path / "ecosystem.yaml"
    descriptor_path.write_text(
        yaml.safe_dump(
            {
                "organisation": {"name": "Acme", "slug": "acme"},
                "projects": [
                    {"name": "Billing", "slug": "acme-billing", "github_repo": "acme/acme-billing"},
                    {"name": "Portal", "slug": "acme-portal", "github_repo": "acme/acme-portal"},
                ],
            }
        )
    )

    report = await seed_from_descriptor(db_session, descriptor_path, workspace_root=tmp_path)

    assert report.organisation_slug == "acme"
    assert {p.slug for p in report.projects} == {"acme-billing", "acme-portal"}
    assert report.skipped == []


@pytest.mark.asyncio
async def test_ingest_org_skips_unresolvable_member(db_session: AsyncSession) -> None:
    descriptor = {
        "organisation": {"name": "Acme", "slug": "acme"},
        "projects": [
            {"slug": "ok", "github_repo": "acme/ok"},
            {"slug": "missing", "github_repo": "acme/missing"},
        ],
    }
    report = await ManifestIngestService(db_session, engine=FakeEngine()).ingest_org(
        descriptor, FakeResolver({"acme/ok": VALID_MANIFEST})
    )

    assert [p.slug for p in report.projects] == ["ok"]
    assert len(report.skipped) == 1 and report.skipped[0]["slug"] == "missing"
