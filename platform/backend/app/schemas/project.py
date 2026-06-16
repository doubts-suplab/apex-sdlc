from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectType = Literal["spring-boot", "angular", "shared-lib", "mainframe", "python", "generic"]
PhaseType = Literal[
    "requirements", "architecture", "development", "testing", "cicd", "docs", "governance"
]
ProjectStatus = Literal["active", "paused", "archived"]


class ProjectCreate(BaseModel):
    """Payload for creating a new project."""

    model_config = ConfigDict(extra="forbid")

    organisation_id: uuid.UUID = Field(..., description="Owning organisation UUID")
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    description: str | None = Field(default=None)
    project_type: ProjectType = Field(default="generic")
    github_repo: str | None = Field(default=None, description="e.g. myorg/my-repo")
    jira_board_id: str | None = Field(default=None)
    confluence_space_key: str | None = Field(default=None)
    current_phase: PhaseType = Field(default="requirements")
    status: ProjectStatus = Field(default="active")


class ProjectUpdate(BaseModel):
    """Payload for partial-update of a project (all fields optional)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    description: str | None = Field(default=None)
    project_type: ProjectType | None = Field(default=None)
    github_repo: str | None = Field(default=None)
    jira_board_id: str | None = Field(default=None)
    confluence_space_key: str | None = Field(default=None)
    current_phase: PhaseType | None = Field(default=None)
    status: ProjectStatus | None = Field(default=None)


class ProjectResponse(BaseModel):
    """Read-side representation of a project."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    project_type: str
    github_repo: str | None
    jira_board_id: str | None
    confluence_space_key: str | None
    current_phase: str
    status: str
    created_at: datetime
    updated_at: datetime
