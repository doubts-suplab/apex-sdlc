"""Slack Web API client — minimal, async, config-driven.

Base URL is configurable (``SLACK_BASE_URL``) so it can point at the real API or a mock server; the bot
token comes from ``SLACK_BOT_TOKEN``. Only the surface the DevOps flow needs (``chat.postMessage``) is
implemented.
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.integrations.errors import IntegrationError

logger = get_logger(__name__)


class SlackClient:
    """Async Slack Web API client."""

    def __init__(self, token: str, base_url: str = "https://slack.com/api") -> None:
        self._token = token
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}

    async def post_message(self, channel: str, text: str) -> dict:
        """Post a message to a channel via ``chat.postMessage``.

        Returns the Slack response (with ``ts`` and ``channel``). Slack signals logical failures with
        ``ok: false`` in a 200 body, so that is surfaced as an ``IntegrationError`` too.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base}/chat.postMessage",
                headers=self._headers,
                json={"channel": channel, "text": text},
            )
        if not response.is_success:
            raise IntegrationError(
                integration="slack",
                message=f"chat.postMessage → HTTP {response.status_code}",
                status_code=response.status_code,
            )
        data = response.json()
        if not data.get("ok", False):
            raise IntegrationError(
                integration="slack", message=f"Slack error: {data.get('error', 'unknown')}"
            )
        return data
