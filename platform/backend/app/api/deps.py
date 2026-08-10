"""Shared API dependencies — project-membership enforcement.

``require_project_member`` binds a bearer token's subject to a project ``Member`` at request time. It is
**opt-in** (``settings.MEMBERSHIP_REQUIRED``, default off) so the offline demo and existing tests keep
working; when enabled it rejects any project write whose token subject is not a member of that project.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException

from app.core.config import get_settings
from app.core.security import CurrentPrincipal, Principal
from app.db.session import DbSession
from app.services.member_service import MemberService


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
