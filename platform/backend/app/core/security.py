"""Auth primitives — HS256 JWT issue/verify + persona RBAC dependencies.

Deliberately **dependency-free**: HS256 is HMAC-SHA256, which the standard library already provides,
so the platform gains JWT auth without pulling in ``pyjwt``/``python-jose`` (and their
``cryptography`` build, unavailable in the offline test env). For RS256/asymmetric keys later, swap
``_sign`` for a ``cryptography``-backed signer behind the same
``create_access_token`` / ``decode_access_token`` interface — callers do not change.

Claims: ``sub`` (subject/user id), ``persona`` (one of :data:`app.agents.catalog.PERSONAS`),
optional ``org_id``, plus ``iat`` / ``exp``. RBAC is enforced per-route via :func:`require_persona`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.agents.catalog import PERSONAS
from app.core.config import get_settings

_ALG = "HS256"
_HEADER = {"alg": _ALG, "typ": "JWT"}
DEFAULT_TTL_SECONDS = 3600


class InvalidTokenError(Exception):
    """Raised when a token is malformed, mis-signed, or expired."""


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _sign(signing_input: bytes) -> str:
    secret = get_settings().SECRET_KEY.encode("utf-8")
    digest = hmac.new(secret, signing_input, hashlib.sha256).digest()
    return _b64url_encode(digest)


def create_access_token(
    *,
    subject: str,
    persona: str,
    organisation_id: str | None = None,
    expires_in: int = DEFAULT_TTL_SECONDS,
) -> str:
    """Mint a signed HS256 JWT carrying the subject, persona, and optional org."""
    if persona not in PERSONAS:
        raise ValueError(f"Unknown persona {persona!r}; expected one of {PERSONAS}")
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": subject, "persona": persona, "iat": now, "exp": now + expires_in,
    }
    if organisation_id is not None:
        payload["org_id"] = organisation_id
    header_b64 = _b64url_encode(json.dumps(_HEADER, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    return f"{header_b64}.{payload_b64}.{_sign(signing_input)}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify signature + expiry and return claims. Raises :class:`InvalidTokenError` on failure."""
    try:
        header_b64, payload_b64, sig = token.split(".")
    except ValueError as exc:
        raise InvalidTokenError("token is not a well-formed JWT") from exc

    expected = _sign(f"{header_b64}.{payload_b64}".encode("ascii"))
    # Constant-time comparison — never leak signature validity via timing.
    if not hmac.compare_digest(sig, expected):
        raise InvalidTokenError("bad signature")

    try:
        claims: dict[str, Any] = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidTokenError("undecodable payload") from exc

    if int(claims.get("exp", 0)) < int(time.time()):
        raise InvalidTokenError("token expired")
    return claims


@dataclass(frozen=True)
class Principal:
    """The authenticated caller resolved from a bearer token."""

    subject: str
    persona: str
    organisation_id: str | None = None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "type": "https://apex-sdlc/errors/unauthorized",
            "title": "Unauthorized",
            "status": 401,
            "detail": detail,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


_bearer = HTTPBearer(auto_error=False)


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    """FastAPI dependency: resolve the bearer token to a :class:`Principal` (401 if invalid)."""
    if credentials is None or not credentials.credentials:
        raise _unauthorized("missing bearer token")
    try:
        claims = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise _unauthorized(str(exc)) from exc
    return Principal(
        subject=str(claims.get("sub", "")),
        persona=str(claims.get("persona", "")),
        organisation_id=claims.get("org_id"),
    )


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


def require_persona(*allowed: str) -> Callable[[Principal], Principal]:
    """Return a dependency that admits only the listed personas (403 otherwise)."""

    allowed_set = frozenset(allowed)

    def _guard(principal: CurrentPrincipal) -> Principal:
        if principal.persona not in allowed_set:
            raise HTTPException(
                status_code=403,
                detail={
                    "type": "https://apex-sdlc/errors/forbidden",
                    "title": "Forbidden",
                    "status": 403,
                    "detail": (
                        f"Persona {principal.persona!r} may not perform this action; "
                        f"requires one of {sorted(allowed_set)}."
                    ),
                },
            )
        return principal

    return _guard
