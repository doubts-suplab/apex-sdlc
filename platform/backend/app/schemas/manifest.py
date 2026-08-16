from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ManifestRead(BaseModel):
    """The persisted eeik-manifest posture for a project."""

    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    domain: str | None
    governance_profile: str | None
    coverage_threshold: int | None
    compliance_frameworks: list[str]
    resolved_packs: list[str]
    engine: str | None = Field(description="Which engine validated: sdk | mcp | vendored.")
    source_ref: str | None = Field(description="Provenance: where the manifest was read from.")
    raw: dict[str, Any] = Field(description="The full manifest as ingested (no fidelity loss).")
    created_at: datetime
    updated_at: datetime


class ManifestIngestRequest(BaseModel):
    """Ingest/refresh a single project's manifest (inline)."""

    model_config = ConfigDict(extra="forbid")

    manifest: dict[str, Any] = Field(..., description="An eeik project-manifest as a mapping.")
    source_ref: str = Field(default="", description="Provenance: where the manifest came from.")


class OrgIngestRequest(BaseModel):
    """Ingest an organisation from a tool-agnostic descriptor (identity + member projects)."""

    model_config = ConfigDict(extra="forbid")

    descriptor: dict[str, Any] = Field(
        ..., description="Org descriptor: `organisation` identity + `projects` (github_repo + manifest_path)."
    )
    workspace_root: str | None = Field(
        default=None,
        description="Local root holding sibling repo checkouts. Falls back to ECOSYSTEM_WORKSPACE_ROOT.",
    )


class IngestedProjectResponse(BaseModel):
    """Per-project outcome of an org ingest."""

    slug: str
    project_id: str
    created: bool
    engine: str
    resolved_packs: list[str]


class IngestReportResponse(BaseModel):
    """Result of ingesting a whole org descriptor."""

    organisation_id: str
    organisation_slug: str
    engine: str
    projects: list[IngestedProjectResponse]
    skipped: list[dict[str, str]]
