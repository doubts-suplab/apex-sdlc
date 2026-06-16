from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IntegrationCreate(BaseModel):
    """Payload for creating a new project integration."""

    integration_type: str = Field(
        ...,
        description="Integration type: github | jira | rally | confluence",
        pattern="^(github|jira|rally|confluence)$",
    )
    config: dict = Field(
        default_factory=dict,
        description="Integration-specific config (e.g. {\"repo\": \"org/repo\"})",
    )
    credentials_ref: str | None = Field(
        default=None,
        description="AWS Secrets Manager secret name, or 'env' for local dev",
    )
    enabled: bool = Field(default=True, description="Whether this integration is active")


class IntegrationUpdate(BaseModel):
    """Payload for partially updating an existing project integration."""

    config: dict | None = Field(default=None, description="Updated integration config")
    credentials_ref: str | None = Field(default=None, description="Updated credentials ref")
    enabled: bool | None = Field(default=None, description="Enable or disable the integration")


class IntegrationResponse(BaseModel):
    """Response schema for a project integration record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    integration_type: str
    config: dict
    credentials_ref: str | None
    enabled: bool
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
