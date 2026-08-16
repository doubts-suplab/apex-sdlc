"""Shared API dependencies — project-membership enforcement.

``require_project_member`` binds a bearer token's subject to a project ``Member`` at request time. It is
**opt-in** (``settings.MEMBERSHIP_REQUIRED``, default off) so the offline demo and existing tests keep
working; when enabled it rejects any project write whose token subject is not a member of that project.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import (
    CurrentPrincipal,
    InvalidTokenError,
    Principal,
    decode_access_token,
)
from app.db.session import DbSession
from app.integrations.github.client import GitHubClient
from app.services.member_service import MemberService

_optional_bearer = HTTPBearer(auto_error=False)


def get_optional_subject(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_optional_bearer)],
) -> str:
    """Best-effort actor id for audit purposes — never rejects the request.

    Returns the bearer token's subject when a valid token is present, else ``"operator"`` so
    unauthenticated (offline / auth-disabled) callers still record a meaningful actor on the audit
    trail. Distinct from :data:`CurrentPrincipal`, which 401s on a missing/invalid token.
    """
    if credentials is None or not credentials.credentials:
        return "operator"
    try:
        subject = str(decode_access_token(credentials.credentials).get("sub", ""))
    except InvalidTokenError:
        return "operator"
    return subject or "operator"


OptionalSubject = Annotated[str, Depends(get_optional_subject)]


def get_github_client() -> GitHubClient:
    """Build a GitHub client from settings.

    A FastAPI dependency so it can be overridden in tests with a fake client (no network), the same
    way ``get_db`` is overridden. Production wiring reads the token and API base from settings.
    """
    settings = get_settings()
    return GitHubClient(settings.GITHUB_TOKEN, base_url=settings.GITHUB_API_BASE)


async def require_project_member(
    project_id: uuid.UUID,
    principal: CurrentPrincipal,
    db: DbSession,
) -> Principal:
    """Ensure the caller is a Member of ``project_id`` (only enforced when MEMBERSHIP_REQUIRED)."""
    if not get_settings().MEMBERSHIP_REQUIRED:
        return principal
    member = await MemberService(db).get_member(project_id, principal.subject)
    if member is None:
        raise HTTPException(
            status_code=403,
            detail={
                "type": "https://apex-sdlc/errors/not-a-member",
                "title": "Not a Project Member",
                "status": 403,
                "detail": (
                    f"Subject {principal.subject!r} is not a member of project {project_id}; "
                    "membership is required for this action."
                ),
            },
        )
    return principal
