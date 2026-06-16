from __future__ import annotations


class IntegrationError(Exception):
    """Raised when an external integration call fails."""

    def __init__(
        self,
        integration: str,
        message: str,
        status_code: int | None = None,
    ) -> None:
        self.integration = integration
        self.status_code = status_code
        super().__init__(f"[{integration}] {message}")
