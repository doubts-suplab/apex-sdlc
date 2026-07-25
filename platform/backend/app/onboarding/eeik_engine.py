"""Consume the real EEIK engine — as a library (SDK) or over MCP.

Historically APEX *vendored* eeik data under ``eeik_assets/`` and re-implemented manifest validation
and pack resolution so it could onboard standalone. Now that eeik ships a governed generation engine
with a stable public surface, APEX can consume the **real** engine instead — one source of truth for
schema, governance rules, and capability resolution.

Two interchangeable backends behind one ``EeikEngine`` interface:

- **SDK (default)** — ``import eeik`` and call the typed API in-process (eeik ADR-007). Fast, no process.
- **MCP (option)** — spawn ``eeik mcp`` and call its tools over the Model Context Protocol (eeik
  ADR-006). Useful when eeik runs as a separate service or in another runtime.

Both are **optional**: if neither eeik (for SDK) nor an ``eeik`` command + ``mcp`` (for MCP) is
available, ``get_engine`` returns ``None`` and callers fall back to the vendored offline path — APEX
still onboards standalone. Select with ``EEIK_MODE=sdk|mcp`` (or pass ``mode=``).

    engine = get_engine()                 # sdk if eeik is importable, else None
    if engine:
        result = engine.validate(manifest)          # {"valid": bool, "errors": [...], "warnings": [...]}
        packs  = engine.resolve_packs(manifest)      # ["core", "architecture", "java", ...]
"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EeikEngine(Protocol):
    """The subset of the EEIK read model APEX onboarding consumes."""

    mode: str

    def validate(self, manifest: dict[str, Any]) -> dict[str, Any]: ...
    def resolve_packs(self, manifest: dict[str, Any]) -> list[str]: ...
    def catalog(self, tag: str | None = None) -> list[dict[str, Any]]: ...
    def verify(self) -> dict[str, Any]: ...


# ── SDK backend (in-process) ──────────────────────────────────────────────────

class SdkEngine:
    """Calls the eeik SDK directly. Requires the ``eeik`` package to be importable."""

    mode = "sdk"

    def __init__(self) -> None:
        import eeik  # raises ImportError if the package is not installed

        self._eeik = eeik

    def validate(self, manifest: dict[str, Any]) -> dict[str, Any]:
        return self._eeik.validate_manifest(manifest=manifest).to_dict()

    def resolve_packs(self, manifest: dict[str, Any]) -> list[str]:
        return self._eeik.resolve_packs(manifest=manifest)

    def catalog(self, tag: str | None = None) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._eeik.find_packs(tag=tag)]

    def verify(self) -> dict[str, Any]:
        return self._eeik.verify().to_dict()


# ── MCP backend (out-of-process, over the protocol) ───────────────────────────

class McpEngine:
    """Calls the EEIK MCP server (``eeik mcp``) over stdio. Requires the ``mcp`` client + ``eeik`` cmd."""

    mode = "mcp"

    def __init__(self, command: str = "eeik", args: tuple[str, ...] = ("mcp",)) -> None:
        import mcp  # noqa: F401  (fail fast if the client SDK is absent)

        self._command = command
        self._args = list(args)

    def _call(self, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        import anyio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=self._command, args=self._args)

        async def _run() -> Any:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, arguments or {})
                    return json.loads(result.content[0].text)

        return anyio.run(_run)

    def validate(self, manifest: dict[str, Any]) -> dict[str, Any]:
        return self._call("eeik_validate_manifest", {"content": json.dumps(manifest)})

    def resolve_packs(self, manifest: dict[str, Any]) -> list[str]:
        return self._call("eeik_resolve_packs", {"content": json.dumps(manifest)}).get("resolved", [])

    def catalog(self, tag: str | None = None) -> list[dict[str, Any]]:
        args = {"tag": tag} if tag else {}
        return self._call("eeik_catalog", args).get("packs", [])

    def verify(self) -> dict[str, Any]:
        return self._call("eeik_verify")


# ── selection ─────────────────────────────────────────────────────────────────

def get_engine(mode: str | None = None) -> EeikEngine | None:
    """Return an EEIK engine for the requested mode, or ``None`` if unavailable.

    ``mode`` defaults to ``$EEIK_MODE`` then ``"sdk"``. Availability is best-effort: a backend whose
    dependencies are missing yields ``None`` so callers transparently fall back to the vendored path.
    """
    mode = (mode or os.environ.get("EEIK_MODE") or "sdk").lower()
    try:
        if mode == "sdk":
            return SdkEngine()
        if mode == "mcp":
            return McpEngine()
    except ImportError:
        return None
    return None
