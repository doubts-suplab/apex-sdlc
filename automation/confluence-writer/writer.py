"""
APEX Confluence Writer
Creates and updates Confluence pages via the REST API v2.

Used by:
  - automation/jira-bridge/handler.py
  - Any APEX automation that needs to write to Confluence

Usage:
    from confluence_writer import ConfluenceWriter

    writer = ConfluenceWriter(
        base_url="https://your-org.atlassian.net/wiki",
        space_key="APEX",
        username="bot@company.com",
        api_token="...",
    )
    writer.create_or_update_page(
        title="My Page Title",
        body="<p>HTML content</p>",
        parent_title="APEX AI Briefs",
    )
"""

import logging
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class ConfluenceWriter:
    """Thin wrapper around the Confluence REST API v2."""

    def __init__(
        self,
        base_url: str,
        space_key: str,
        username: str,
        api_token: str,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._space_key = space_key
        self._auth = HTTPBasicAuth(username, api_token)
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_or_update_page(
        self,
        title: str,
        body: str,
        parent_title: Optional[str] = None,
    ) -> dict:
        """Create a page if it doesn't exist; update it if it does."""
        existing = self._find_page_by_title(title)
        if existing:
            return self._update_page(existing["id"], existing["version"]["number"], title, body)
        parent_id = self._find_or_create_parent(parent_title) if parent_title else None
        return self._create_page(title, body, parent_id)

    def append_to_page(self, title: str, content: str) -> dict:
        """Append HTML content to an existing page."""
        page = self._find_page_by_title(title)
        if page is None:
            logger.warning("Cannot append — page not found: %s", title)
            return {}
        current_body = self._get_page_body(page["id"])
        new_body = current_body + "\n<hr/>\n" + content
        return self._update_page(page["id"], page["version"]["number"], title, new_body)

    def create_page_from_template(
        self,
        title: str,
        template: str,
        variables: dict[str, str],
        parent_title: Optional[str] = None,
    ) -> dict:
        """Render a simple {variable} template and create a page."""
        body = template
        for key, value in variables.items():
            body = body.replace(f"{{{key}}}", value)
        return self.create_or_update_page(title, body, parent_title)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _api(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self._base}/rest/api/content{path}"
        response = requests.request(
            method, url, auth=self._auth, headers=self._headers, **kwargs
        )
        if not response.ok:
            logger.error(
                "Confluence API error %s %s → %s %s",
                method,
                url,
                response.status_code,
                response.text[:500],
            )
            response.raise_for_status()
        return response

    def _find_page_by_title(self, title: str) -> Optional[dict]:
        """Return the page dict if found, None otherwise."""
        response = self._api(
            "GET",
            "",
            params={
                "title": title,
                "spaceKey": self._space_key,
                "expand": "version",
            },
        )
        results = response.json().get("results", [])
        return results[0] if results else None

    def _get_page_body(self, page_id: str) -> str:
        response = self._api("GET", f"/{page_id}", params={"expand": "body.storage"})
        return response.json()["body"]["storage"]["value"]

    def _create_page(
        self,
        title: str,
        body: str,
        parent_id: Optional[str] = None,
    ) -> dict:
        payload: dict = {
            "type": "page",
            "title": title,
            "space": {"key": self._space_key},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        response = self._api("POST", "", json=payload)
        created = response.json()
        logger.info("Created Confluence page: %s (id=%s)", title, created.get("id"))
        return created

    def _update_page(self, page_id: str, current_version: int, title: str, body: str) -> dict:
        payload = {
            "type": "page",
            "title": title,
            "version": {"number": current_version + 1},
            "body": {"storage": {"value": body, "representation": "storage"}},
        }
        response = self._api("PUT", f"/{page_id}", json=payload)
        updated = response.json()
        logger.info("Updated Confluence page: %s (id=%s, v%s)", title, page_id, current_version + 1)
        return updated

    def _find_or_create_parent(self, parent_title: str) -> Optional[str]:
        """Find the parent page; create it as a root page if missing."""
        parent = self._find_page_by_title(parent_title)
        if parent:
            return parent["id"]
        logger.info("Parent page '%s' not found — creating it", parent_title)
        created = self._create_page(
            title=parent_title,
            body=f"<p>Auto-created by APEX Automation — parent page for: {parent_title}</p>",
        )
        return created["id"]
