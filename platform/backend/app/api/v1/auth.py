"""Auth API — issue a bearer token and report the current principal.

``POST /auth/token`` mints an HS256 JWT for a subject + persona (dev/identity-broker login; a real
credential exchange is the follow-on). ``GET /auth/me`` echoes the authenticated principal — the
smallest end-to-end proof that the token round-trips through the RBAC dependency.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.catalog import PERSONAS
from app.core.security import (
    DEFAULT_TTL_SECONDS,
    CurrentPrincipal,
    create_access_token,
)
from app.schemas.auth import TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse, summary="Issue a bearer token for a persona")
async def issue_token(body: TokenRequest) -> TokenResponse:
    if body.persona not in PERSONAS:
        raise HTTPException(
            status_code=422,
            detail={
                "type": "https://apex-sdlc/errors/unknown-persona",
                "title": "Unknown Persona",
                "status": 422,
                "detail": f"Persona {body.persona!r} is not one of {sorted(PERSONAS)}.",
            },
        )
    token = create_access_token(
        subject=body.subject,
        persona=body.persona,
        organisation_id=body.organisation_id,
    )
    return TokenResponse(access_token=token, expires_in=DEFAULT_TTL_SECONDS, persona=body.persona)


@router.get("/me", summary="Return the authenticated principal")
async def read_me(principal: CurrentPrincipal) -> dict[str, str | None]:
    return {
        "subject": principal.subject,
        "persona": principal.persona,
        "organisation_id": principal.organisation_id,
    }
