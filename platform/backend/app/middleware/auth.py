"""Global auth middleware — opt-in, allowlist-based JWT enforcement.

When ``settings.AUTH_REQUIRED`` is true, every request must carry a valid bearer token except for an
allowlist (health, the OpenAPI docs, and the token endpoint itself). Off by default so the offline demo
endpoints stay open; production flips it on. The per-route ``require_persona(...)`` RBAC dependency still
applies on top of this — this middleware only enforces *authentication*, not authorization.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.security import InvalidTokenError, decode_access_token

# Exact paths and prefixes that never require auth (mirrors platform CLAUDE.md's allowlist).
_ALLOW_EXACT = {"/", "/health", "/openapi.json", "/api/v1/health", "/api/v1/auth/token"}
_ALLOW_PREFIXES = ("/docs", "/redoc", "/api/v1/auth/token")


def _is_allowlisted(path: str) -> bool:
    return path in _ALLOW_EXACT or path.startswith(_ALLOW_PREFIXES)


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "type": "https://apex-sdlc/errors/unauthorized",
            "title": "Unauthorized",
            "status": 401,
            "detail": detail,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforce authentication globally when ``AUTH_REQUIRED`` is set."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not get_settings().AUTH_REQUIRED or _is_allowlisted(request.url.path):
            return await call_next(request)

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return _unauthorized("missing bearer token")
        try:
            claims = decode_access_token(header[len("Bearer ") :])
        except InvalidTokenError as exc:
            return _unauthorized(str(exc))

        # Expose the principal for downstream handlers/logging; RBAC deps re-decode as needed.
        request.state.principal = claims
        return await call_next(request)
