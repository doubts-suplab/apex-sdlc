from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class PortfolioProjectRow(BaseModel):
    """Per-project delivery rollup within an organisation's portfolio."""

    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    name: str
    slug: str
    github_repo: str | None
    delivery_count: int
    estimate_points: int = Field(
        description="Sum of estimate_points across the project's deliveries (unsized count as 0)."
    )
    open_count: int = Field(
        description="Deliveries not yet done or dropped (proposed + planned + in_progress)."
    )
    # Governed posture from the project's ingested eeik manifest (null when none has been ingested).
    domain: str | None = Field(default=None, description="Manifest domain (e.g. generic, banking).")
    governance_profile: str | None = Field(
        default=None, description="Manifest governance profile (e.g. enterprise)."
    )
    compliance_frameworks: list[str] = Field(
        default_factory=list, description="Compliance frameworks the manifest declares (e.g. gdpr)."
    )
    coverage_threshold: int | None = Field(
        default=None, description="Manifest coverage gate, if set."
    )
    resolved_pack_count: int | None = Field(
        default=None, description="Number of eeik capability packs the manifest resolves."
    )
    manifest_engine: str | None = Field(
        default=None, description="Which engine validated the manifest: sdk | mcp | vendored."
    )


class PortfolioSummary(BaseModel):
    """Cross-project delivery rollup for one organisation — the ecosystem planning view.

    Aggregates every delivery belonging to the organisation's projects into portfolio totals
    (counts by status and priority, total estimate points) plus a per-project breakdown, so an
    operator can see the whole ecosystem's delivery state rather than one project at a time.
    """

    organisation_id: uuid.UUID
    project_count: int
    delivery_count: int
    open_count: int
    total_estimate_points: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    projects: list[PortfolioProjectRow]
