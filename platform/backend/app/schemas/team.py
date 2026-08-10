from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.agents.catalog import PERSONAS

_PERSONA_PATTERN = "^(" + "|".join(PERSONAS) + ")$"


class TeamCreate(BaseModel):
    """Payload for creating a team within an organisation."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(
        ..., min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    description: str | None = Field(default=None)


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisation_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    created_at: datetime


class MemberCreate(BaseModel):
    """Payload for adding a member (persona holder) to a project."""

    model_config = ConfigDict(extra="forbid")

    subject: str = Field(..., min_length=1, max_length=255, description="Identity subject (JWT sub)")
    persona: str = Field(..., pattern=_PERSONA_PATTERN)
    display_name: str = Field(default="", max_length=255)
    email: str | None = Field(default=None, max_length=320)
    team_id: uuid.UUID | None = Field(default=None)


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    team_id: uuid.UUID | None = None
    subject: str
    persona: str
    display_name: str
    email: str | None = None
    created_at: datetime
