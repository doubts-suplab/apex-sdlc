from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger
from app.integrations.errors import IntegrationError

logger = get_logger(__name__)


class ConfluenceClient:
    """Async Confluence REST API v2 client."""

    def __init__(self, base_url: str, email: str, token: str) -> None:
        self._base = base_url.rstrip("/") + "/wiki/api/v2"
        self._auth = httpx.BasicAuth(email, token)
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an authenticated Confluence API v2 request."""
        url = f"{self._base}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                auth=self._auth,
                headers=self._headers,
                **kwargs,
            )

        if not response.is_success:
            body = response.text[:500]
            logger.warning(
                "confluence.request_error",
                method=method,
                path=path,
                status=response.status_code,
                body=body,
            )
            raise IntegrationError(
                integration="confluence",
                message=f"{method} {path} → HTTP {response.status_code}: {body}",
                status_code=response.status_code,
            )

        if response.content:
            return response.json()
        return {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_spaces(self) -> list[dict]:
        """List all Confluence spaces the authenticated user can access.

        Returns:
            List of space objects (``id``, ``key``, ``name``, ``type``).
        """
        results: list[dict] = []
        cursor: str | None = None

        while True:
            params: dict[str, Any] = {"limit": 25}
            if cursor:
                params["cursor"] = cursor

            data = await self._request("GET", "/spaces", params=params)
            results.extend(data.get("results", []))

            links = data.get("_links", {})
            next_url = links.get("next")
            if not next_url:
                break

            # Extract cursor from the next link
            # next_url is a relative path like /wiki/api/v2/spaces?cursor=XYZ
            import urllib.parse
            parsed = urllib.parse.urlparse(next_url)
            qs = urllib.parse.parse_qs(parsed.query)
            cursor = qs.get("cursor", [None])[0]
            if not cursor:
                break

        return results

    async def get_space_pages(self, space_key: str, limit: int = 25) -> list[dict]:
        """List pages in a Confluence space.

        Args:
            space_key: Space key (e.g. ``"APEX"``).
            limit: Maximum number of pages to return.

        Returns:
            List of page objects with ``id``, ``title``, ``version``.
        """
        # v2 API uses space ID not key; fetch the space first
        spaces = await self.get_spaces()
        space = next((s for s in spaces if s.get("key") == space_key), None)
        if not space:
            raise IntegrationError(
                integration="confluence",
                message=f"Space with key {space_key!r} not found.",
            )

        data = await self._request(
            "GET",
            "/pages",
            params={"spaceId": space["id"], "limit": limit},
        )
        return data.get("results", [])

    async def create_page(
        self,
        space_key: str,
        title: str,
        body_html: str,
        parent_id: str | None = None,
    ) -> dict:
        """Create a new Confluence page.

        Args:
            space_key: Space key for the new page.
            title: Page title (must be unique within the space).
            body_html: Page body in Confluence storage format (XHTML).
            parent_id: Optional parent page ID; creates as root page if omitted.

        Returns:
            Created page object with ``id``, ``title``, ``version``.
        """
        spaces = await self.get_spaces()
        space = next((s for s in spaces if s.get("key") == space_key), None)
        if not space:
            raise IntegrationError(
                integration="confluence",
                message=f"Space with key {space_key!r} not found.",
            )

        payload: dict[str, Any] = {
            "spaceId": space["id"],
            "status": "current",
            "title": title,
            "body": {
                "representation": "storage",
                "value": body_html,
            },
        }
        if parent_id:
            payload["parentId"] = parent_id

        created = await self._request("POST", "/pages", json=payload)
        logger.info("confluence.page_created", title=title, page_id=created.get("id"))
        return created

    async def update_page(
        self,
        page_id: str,
        title: str,
        body_html: str,
        version: int,
    ) -> dict:
        """Update an existing Confluence page.

        Args:
            page_id: Numeric page ID.
            title: New (or unchanged) page title.
            body_html: New page body in Confluence storage format.
            version: Current version number; will be incremented by 1.

        Returns:
            Updated page object.
        """
        payload: dict[str, Any] = {
            "id": page_id,
            "status": "current",
            "title": title,
            "body": {
                "representation": "storage",
                "value": body_html,
            },
            "version": {"number": version + 1, "message": "Updated by APEX Platform"},
        }

        updated = await self._request("PUT", f"/pages/{page_id}", json=payload)
        logger.info(
            "confluence.page_updated",
            title=title,
            page_id=page_id,
            new_version=version + 1,
        )
        return updated

    async def get_page(self, page_id: str) -> dict:
        """Fetch a single Confluence page by ID (includes body content).

        Args:
            page_id: Numeric page ID.

        Returns:
            Page object with ``id``, ``title``, ``version``, ``body``.
        """
        return await self._request(
            "GET",
            f"/pages/{page_id}",
            params={"body-format": "storage"},
        )
