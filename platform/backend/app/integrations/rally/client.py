from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger
from app.integrations.errors import IntegrationError

logger = get_logger(__name__)

_WSAPI = "/slm/webservice/v2.0"


class RallyClient:
    """Async Rally (CA Agile Central) REST API client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://rally1.rallydev.com",
        workspace_oid: str = "",
    ) -> None:
        self._base = base_url.rstrip("/") + _WSAPI
        self._headers = {
            "zsessionid": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._workspace_oid = workspace_oid

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an authenticated Rally API request and return parsed JSON."""
        url = f"{self._base}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers,
                **kwargs,
            )

        if not response.is_success:
            body = response.text[:500]
            logger.warning(
                "rally.request_error",
                method=method,
                path=path,
                status=response.status_code,
                body=body,
            )
            raise IntegrationError(
                integration="rally",
                message=f"{method} {path} → HTTP {response.status_code}: {body}",
                status_code=response.status_code,
            )

        return response.json()

    def _workspace_ref(self) -> str | None:
        if self._workspace_oid:
            return f"/workspace/{self._workspace_oid}"
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_iterations(
        self,
        project_ref: str,
        state: str = "Planning",
    ) -> list[dict]:
        """Fetch iterations (sprints) for a Rally project.

        Args:
            project_ref: Full Rally project ref (e.g. ``"/project/12345678"``).
            state: Iteration state filter — ``"Planning"``, ``"Committed"``, ``"Accepted"``.

        Returns:
            List of Iteration objects from the QueryResult.
        """
        params: dict[str, Any] = {
            "project": project_ref,
            "query": f'(State = "{state}")',
            "fetch": "Name,State,StartDate,EndDate,PlannedVelocity",
            "pagesize": 200,
            "order": "StartDate DESC",
        }

        ws_ref = self._workspace_ref()
        if ws_ref:
            params["workspace"] = ws_ref

        data = await self._request("GET", "/iteration", params=params)
        return data.get("QueryResult", {}).get("Results", [])

    async def get_active_iteration(self, project_ref: str) -> dict | None:
        """Return the currently active (Committed) iteration, or None.

        Args:
            project_ref: Full Rally project ref.

        Returns:
            Iteration dict, or ``None`` if no active iteration found.
        """
        iterations = await self.get_iterations(project_ref, state="Committed")
        return iterations[0] if iterations else None

    async def get_user_stories(
        self,
        project_ref: str,
        iteration_ref: str | None = None,
    ) -> list[dict]:
        """Fetch HierarchicalRequirement (User Story) objects.

        Args:
            project_ref: Full Rally project ref.
            iteration_ref: Optional full Rally iteration ref to filter by.

        Returns:
            List of user story dicts.
        """
        query_parts = []
        if iteration_ref:
            query_parts.append(f'(Iteration = "{iteration_ref}")')

        query = " AND ".join(query_parts) if query_parts else ""

        params: dict[str, Any] = {
            "project": project_ref,
            "fetch": "Name,State,PlanEstimate,Iteration,Description,FormattedID",
            "pagesize": 200,
            "order": "Rank",
        }
        if query:
            params["query"] = query

        ws_ref = self._workspace_ref()
        if ws_ref:
            params["workspace"] = ws_ref

        data = await self._request("GET", "/hierarchicalrequirement", params=params)
        return data.get("QueryResult", {}).get("Results", [])

    async def create_user_story(
        self,
        workspace_ref: str,
        project_ref: str,
        name: str,
        description: str,
        plan_estimate: float | None = None,
    ) -> dict:
        """Create a Rally User Story (HierarchicalRequirement).

        Args:
            workspace_ref: Full Rally workspace ref (e.g. ``"/workspace/12345678"``).
            project_ref: Full Rally project ref.
            name: Story name/title.
            description: Story description (HTML supported).
            plan_estimate: Optional story point estimate.

        Returns:
            Created HierarchicalRequirement object (``CreateResult`` wrapper).
        """
        story: dict[str, Any] = {
            "Workspace": workspace_ref,
            "Project": project_ref,
            "Name": name,
            "Description": description,
        }
        if plan_estimate is not None:
            story["PlanEstimate"] = plan_estimate

        data = await self._request(
            "POST",
            "/hierarchicalrequirement/create",
            json={"HierarchicalRequirement": story},
        )
        result = data.get("CreateResult", {})
        if result.get("Errors"):
            raise IntegrationError(
                integration="rally",
                message=f"Failed to create user story: {result['Errors']}",
            )
        logger.info(
            "rally.story_created",
            object_ref=result.get("Object", {}).get("_ref"),
        )
        return result.get("Object", {})

    async def get_project(self, project_oid: str) -> dict:
        """Fetch a Rally project by OID.

        Args:
            project_oid: Numeric Rally project OID.

        Returns:
            Project object from the Rally API.
        """
        data = await self._request("GET", f"/project/{project_oid}")
        return data.get("Project", {})

    async def find_project_by_name(self, name: str) -> dict | None:
        """Search for a Rally project by exact name.

        Args:
            name: Project name to search for.

        Returns:
            Project dict if found, or ``None``.
        """
        params: dict[str, Any] = {
            "query": f'(Name = "{name}")',
            "fetch": "Name,State,ObjectID",
            "pagesize": 1,
        }

        ws_ref = self._workspace_ref()
        if ws_ref:
            params["workspace"] = ws_ref

        data = await self._request("GET", "/project", params=params)
        results = data.get("QueryResult", {}).get("Results", [])
        return results[0] if results else None
