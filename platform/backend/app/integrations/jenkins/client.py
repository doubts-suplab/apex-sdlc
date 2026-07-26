"""Jenkins client — minimal, async, config-driven.

Base URL (``JENKINS_BASE_URL``) plus basic auth (``JENKINS_USER`` / ``JENKINS_API_TOKEN``) come from
config, so the client can target a real controller or a mock server. Only ``buildWithParameters`` (trigger
a job) is implemented — the surface the DevOps flow needs.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger
from app.integrations.errors import IntegrationError

logger = get_logger(__name__)


class JenkinsClient:
    """Async Jenkins client."""

    def __init__(self, base_url: str, user: str, api_token: str) -> None:
        self._base = base_url.rstrip("/")
        self._auth = (user, api_token)

    async def trigger_build(self, job: str, parameters: dict[str, Any] | None = None) -> dict:
        """Trigger a build for ``job`` with optional parameters.

        Jenkins returns 201 with a queue-item ``Location`` header (not a body), so the queue URL is
        surfaced as the result.
        """
        params = parameters or {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base}/job/{job}/buildWithParameters",
                auth=self._auth,
                params=params,
            )
        if not response.is_success:
            raise IntegrationError(
                integration="jenkins",
                message=f"trigger build {job!r} → HTTP {response.status_code}",
                status_code=response.status_code,
            )
        return {"job": job, "queued": True, "queue_url": response.headers.get("Location", "")}
