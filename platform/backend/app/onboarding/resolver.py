"""Resolve a project's eeik manifest from a source — generic, offline-capable.

An org descriptor names each member by ``github_repo`` (``owner/name``) + ``manifest_path``. A resolver
turns that into the parsed manifest dict plus a human-readable ``source_ref`` for provenance. The default
``LocalWorkspaceResolver`` reads from a local multi-repo checkout so APEX can ingest an ecosystem fully
offline; a network-backed ``GitHubResolver`` is a later addition behind the same protocol. Nothing here
is specific to any organisation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml


class ManifestNotFoundError(FileNotFoundError):
    """Raised when a resolver cannot locate or parse a project's manifest."""


@runtime_checkable
class ManifestResolver(Protocol):
    """Fetches the parsed manifest dict + a provenance ``source_ref`` for one descriptor member."""

    def fetch(self, github_repo: str, manifest_path: str) -> tuple[dict[str, Any], str]: ...


class LocalWorkspaceResolver:
    """Reads each project's manifest from a local multi-repo checkout.

    Maps ``owner/repo`` → ``<root>/<repo-basename>/<manifest_path>``. Keying on the repo basename (not the
    owner) means the resolver finds the local checkout regardless of which org the descriptor's
    ``github_repo`` names — the local directory layout is by repo name, not by org.
    """

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).expanduser().resolve()

    def fetch(self, github_repo: str, manifest_path: str) -> tuple[dict[str, Any], str]:
        repo_name = github_repo.split("/")[-1]
        path = self._root / repo_name / manifest_path
        if not path.is_file():
            raise ManifestNotFoundError(
                f"No manifest for {github_repo} at {path} (root={self._root})."
            )
        with path.open() as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ManifestNotFoundError(f"Manifest at {path} is not a YAML mapping.")
        return data, str(path)
