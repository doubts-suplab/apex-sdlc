"""Generic org/manifest ingestion — register projects + persist their governed posture.

APEX ingests an *organisation descriptor* (identity + a list of member projects, each naming a
``github_repo`` + ``manifest_path``) and each member's eeik ``project-manifest.yaml``. Every manifest is
validated through the **real eeik engine** (SDK/MCP) when available — the same authority path as
onboarding (`onboard_with_eeik`) — and its posture is persisted onto a ``ProjectManifestRecord`` (1:1
with ``Project``). When eeik is not installed, ingestion falls back to the vendored offline path and
records ``engine="vendored"`` in provenance.

The whole capability is generic: it names no organisation and is exercised by *data* (e.g. the Aether
ecosystem descriptor), never by organisation-specific code.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.organisation import Organisation
from app.models.project import Project
from app.models.project_manifest import ProjectManifestRecord
from app.onboarding.eeik_engine import EeikEngine, get_engine
from app.onboarding.resolver import ManifestResolver
from app.onboarding.service import ManifestInvalidError, _apex_project_type, _slugify
from app.schemas.project import ProjectCreate
from app.services.project_service import ProjectService

logger = get_logger(__name__)


@dataclass
class IngestedProject:
    """Outcome of ingesting one project's manifest."""

    slug: str
    project_id: str
    created: bool  # True if the Project row was newly created (vs. an existing one updated)
    engine: str  # sdk | mcp | vendored
    resolved_packs: list[str]


@dataclass
class IngestReport:
    """Result of ingesting a whole org descriptor."""

    organisation_id: str
    organisation_slug: str
    engine: str
    projects: list[IngestedProject] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)  # {slug, reason}


class ManifestIngestService:
    """Persists eeik manifests as governed project posture — the generic ingestion seam.

    The eeik engine is injected (or resolved once via ``get_engine``) so tests can drive the flow with a
    fake and offline runs transparently fall back to ``engine="vendored"``.
    """

    def __init__(
        self,
        db: AsyncSession,
        engine: EeikEngine | None = None,
        *,
        mode: str | None = None,
    ) -> None:
        self._db = db
        self._projects = ProjectService(db)
        self._engine = engine if engine is not None else get_engine(mode)

    @property
    def engine_mode(self) -> str:
        return self._engine.mode if self._engine else "vendored"

    # ------------------------------------------------------------------
    # Single manifest → posture on an existing project
    # ------------------------------------------------------------------
    async def attach_manifest(
        self,
        project: Project,
        *,
        manifest: dict,
        source_ref: str = "",
    ) -> ProjectManifestRecord:
        """Validate a manifest via eeik and upsert the project's 1:1 ``ProjectManifestRecord``.

        Raises ``ManifestInvalidError`` (eeik's errors) when the real engine rejects the manifest.
        Idempotent: re-ingesting refreshes the existing record in place.
        """
        resolved_packs: list[str] = []
        if self._engine is not None:
            validation = self._engine.validate(manifest)
            if not validation.get("valid", False):
                raise ManifestInvalidError(validation.get("errors", []))
            resolved_packs = self._engine.resolve_packs(manifest)

        proj = manifest.get("project", {}) or {}
        gov = manifest.get("governance", {}) or {}

        record = await self._get_manifest(project.id)
        if record is None:
            record = ProjectManifestRecord(project_id=project.id)
            self._db.add(record)

        record.domain = proj.get("domain")
        record.governance_profile = gov.get("profile")
        record.coverage_threshold = gov.get("coverage_threshold")
        record.compliance_frameworks = list(gov.get("compliance_frameworks") or [])
        record.resolved_packs = resolved_packs
        record.engine = self.engine_mode
        record.source_ref = source_ref
        record.raw = manifest

        await self._db.flush()
        logger.info(
            "manifest.ingested",
            project_id=str(project.id),
            engine=self.engine_mode,
            packs=len(resolved_packs),
        )
        return record

    # ------------------------------------------------------------------
    # Org descriptor → projects + posture
    # ------------------------------------------------------------------
    async def ingest_org(self, descriptor: dict, resolver: ManifestResolver) -> IngestReport:
        """Register an org descriptor's projects and ingest each member's manifest.

        Idempotent — re-running finds existing projects (by ``github_repo`` then org+slug) and refreshes
        their posture rather than duplicating. A member whose manifest can't be resolved or is invalid is
        recorded in ``report.skipped`` and does not abort the run.
        """
        org_desc = descriptor.get("organisation", {}) or {}
        slug = org_desc.get("slug")
        if not slug:
            raise ValueError("descriptor.organisation.slug is required")
        org = await self._get_or_create_org(
            slug=slug, name=org_desc.get("name") or slug, description=org_desc.get("description")
        )

        report = IngestReport(
            organisation_id=str(org.id), organisation_slug=org.slug, engine=self.engine_mode
        )
        for member in descriptor.get("projects", []) or []:
            repo = member.get("github_repo")
            manifest_path = member.get("manifest_path") or "project-manifest.yaml"
            label = member.get("slug") or repo or "?"
            try:
                manifest, source_ref = resolver.fetch(repo, manifest_path)
            except Exception as exc:  # resolver failures are per-project, not fatal to the run
                report.skipped.append({"slug": label, "reason": str(exc)})
                continue

            project, created = await self._upsert_project(org, member, manifest)
            try:
                record = await self.attach_manifest(
                    project, manifest=manifest, source_ref=source_ref
                )
            except ManifestInvalidError as exc:
                report.skipped.append({"slug": label, "reason": f"invalid manifest: {exc}"})
                continue

            report.projects.append(
                IngestedProject(
                    slug=project.slug,
                    project_id=str(project.id),
                    created=created,
                    engine=self.engine_mode,
                    resolved_packs=record.resolved_packs,
                )
            )

        logger.info(
            "ingest.org.completed",
            organisation_slug=org.slug,
            ingested=len(report.projects),
            skipped=len(report.skipped),
            engine=self.engine_mode,
        )
        return report

    async def get_manifest(self, project_id: uuid.UUID) -> ProjectManifestRecord | None:
        """Return the persisted manifest record for a project, or None."""
        result = await self._db.execute(
            select(ProjectManifestRecord).where(ProjectManifestRecord.project_id == project_id)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _get_manifest(self, project_id: uuid.UUID) -> ProjectManifestRecord | None:
        return await self.get_manifest(project_id)

    async def _get_or_create_org(
        self, *, slug: str, name: str, description: str | None
    ) -> Organisation:
        result = await self._db.execute(select(Organisation).where(Organisation.slug == slug))
        org = result.scalar_one_or_none()
        if org is None:
            org = Organisation(name=name, slug=slug, description=description)
            self._db.add(org)
            await self._db.flush()
            logger.info("ingest.org_created", slug=slug, id=str(org.id))
        return org

    async def _upsert_project(
        self, org: Organisation, member: dict, manifest: dict
    ) -> tuple[Project, bool]:
        repo = member.get("github_repo")
        if repo:
            existing = await self._projects.get_by_github_repo(repo)
            if existing is not None:
                return existing, False

        proj = manifest.get("project", {}) or {}
        slug = member.get("slug") or _slugify(proj.get("name", ""))
        by_slug = await self._get_project_by_org_slug(org.id, slug)
        if by_slug is not None:
            return by_slug, False

        payload = ProjectCreate(
            organisation_id=org.id,
            name=member.get("name") or proj.get("name") or slug,
            slug=slug,
            description=proj.get("description"),
            project_type=_apex_project_type(manifest),
            github_repo=repo,
        )
        return await self._projects.create(payload), True

    async def _get_project_by_org_slug(self, organisation_id: uuid.UUID, slug: str) -> Project | None:
        result = await self._db.execute(
            select(Project).where(
                Project.organisation_id == organisation_id, Project.slug == slug
            )
        )
        return result.scalar_one_or_none()
