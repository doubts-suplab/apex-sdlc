"""Auth request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.agents.catalog import PERSONAS


class TokenRequest(BaseModel):
    """Request a bearer token for a subject acting as a given persona.

    This is a **dev/identity-broker login**: it establishes *who* the caller is and *which persona*
    they hold, but does not yet verify a credential — a real password / OIDC exchange comes later
    (there is no user-credential store in the platform yet). The persona drives RBAC.
    """

    model_config = ConfigDict(extra="forbid")

    subject: str = Field(..., min_length=1, max_length=255, description="User / subject identifier")
    persona: str = Field(..., description=f"One of {PERSONAS}")
    organisation_id: str | None = Field(default=None, description="Optional organisation scope")


class TokenResponse(BaseModel):
    """An issued bearer token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    persona: str
