"""Generic manifest/org ingestion endpoints — how APEX registers and manages a governed portfolio.

These endpoints are organisation-agnostic: they ingest a tool-agnostic org descriptor and eeik
project-manifests supplied as *data*. No organisation is named here. The org-descriptor path resolves each
member's manifest from a local multi-repo checkout (``ECOSYSTEM_WORKSPACE_ROOT``); a network-backed
resolver is a later addition. The single-manifest path takes the manifest inline, so it needs no
workspace and works in any deployment.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.session import DbSession
from app.onboarding.ingest import ManifestIngestService
from app.onboarding.resolver import LocalWorkspaceResolver
from app.onboarding.service import ManifestInvalidError
from app.schemas.common import ProblemDetail
from app.schemas.manifest import (
    IngestReportResponse,
    ManifestIngestRequest,
    ManifestRead,
    OrgIngestRequest,
)
from app.services.project_service import ProjectService

router = APIRouter(tags=["ingestion"])
logger = get_logger(__name__)


def _get_ingest_service(db: DbSession) -> ManifestIngestService:
    return ManifestIngestService(db)


def _get_project_service(db: DbSession) -> ProjectService:
    return ProjectService(db)


IngestSvc = Annotated[ManifestIngestService, Depends(_get_ingest_service)]
ProjSvc = Annotated[ProjectService, Depends(_get_project_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

_PROJECT_NOT_FOUND = ProblemDetail(
    type="https://apex.example.com/problems/not-found",
    title="Project Not Found",
    status=404,
    detail="The requested project does not exist.",
)
_MANIFEST_NOT_FOUND = ProblemDetail(
    type="https://apex.example.com/problems/not-found",
    title="Manifest Not Found",
    status=404,
    detail="No manifest has been ingested for this project.",
)


@router.post(
    "/ingest/organisation",
    response_model=IngestReportResponse,
    responses={400: {"model": ProblemDetail}},
    summary="Ingest an organisation + its projects from a descriptor",
)
async def ingest_organisation(
    body: OrgIngestRequest,
    service: IngestSvc,
    settings: SettingsDep,
) -> IngestReportResponse:
    """Register an org descriptor's projects and ingest each member's eeik manifest.

    Each member's ``project-manifest.yaml`` is resolved from a local multi-repo checkout, validated via
    the real eeik engine (when installed), and persisted as governed posture. Idempotent.
    """
    root = body.workspace_root or settings.ECOSYSTEM_WORKSPACE_ROOT
    if not root:
        raise HTTPException(
            status_code=400,
            detail=ProblemDetail(
                type="https://apex.example.com/problems/bad-request",
                title="No Workspace Root",
                status=400,
                detail="Set ECOSYSTEM_WORKSPACE_ROOT or pass workspace_root to resolve manifests.",
            ).model_dump(),
        )
    resolver = LocalWorkspaceResolver(root)
    try:
        report = await service.ingest_org(body.descriptor, resolver)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=ProblemDetail(
                type="https://apex.example.com/problems/bad-request",
                title="Invalid Descriptor",
                status=400,
                detail=str(exc),
            ).model_dump(),
        ) from exc
    return IngestReportResponse(
        organisation_id=report.organisation_id,
        organisation_slug=report.organisation_slug,
        engine=report.engine,
        projects=[p.__dict__ for p in report.projects],  # type: ignore[arg-type]
        skipped=report.skipped,
    )


@router.post(
    "/projects/{project_id}/manifest",
    response_model=ManifestRead,
    responses={404: {"model": ProblemDetail}, 422: {"model": ProblemDetail}},
    summary="Ingest/refresh a project's eeik manifest (inline)",
)
async def ingest_project_manifest(
    project_id: uuid.UUID,
    body: ManifestIngestRequest,
    service: IngestSvc,
    projects: ProjSvc,
) -> ManifestRead:
    """Attach (or refresh) the eeik-manifest posture for one existing project. Idempotent."""
    project = await projects.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=_PROJECT_NOT_FOUND.model_dump())
    try:
        record = await service.attach_manifest(
            project, manifest=body.manifest, source_ref=body.source_ref
        )
    except ManifestInvalidError as exc:
        raise HTTPException(
            status_code=422,
            detail=ProblemDetail(
                type="https://apex.example.com/problems/invalid-manifest",
                title="Invalid Manifest",
                status=422,
                detail="; ".join(exc.errors) or "manifest is invalid",
            ).model_dump(),
        ) from exc
    return ManifestRead.model_validate(record)


@router.get(
    "/projects/{project_id}/manifest",
    response_model=ManifestRead,
    responses={404: {"model": ProblemDetail}},
    summary="Read a project's ingested manifest posture",
)
async def get_project_manifest(
    project_id: uuid.UUID,
    service: IngestSvc,
    projects: ProjSvc,
) -> ManifestRead:
    """Return the persisted eeik-manifest posture for a project (404 if none has been ingested)."""
    if await projects.get_by_id(project_id) is None:
        raise HTTPException(status_code=404, detail=_PROJECT_NOT_FOUND.model_dump())
    record = await service.get_manifest(project_id)
    if record is None:
        raise HTTPException(status_code=404, detail=_MANIFEST_NOT_FOUND.model_dump())
    return ManifestRead.model_validate(record)
