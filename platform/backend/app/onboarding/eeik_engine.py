"""EEIK engine — resolve a manifest to capability packs, from either vendored assets or a live checkout.

Two engines behind one interface:

- :class:`VendoredEeikEngine` — the deterministic, offline resolver over the snapshot bundled at
  ``eeik_assets/`` (the platform's default; keeps demos/tests reproducible).
- :class:`RepoEeikEngine` — resolves against a **real eeik-bootstrap checkout**: it reads each pack's
  own ``metadata.yaml`` (``manifest_triggers``, ``agents_provided``, ``status``) — the actual eeik
  resolution mechanism — so availability reflects the *live* repo, not a snapshot. Packs the vendored
  copy still marks "planned" (python, react, banking…) show as built once the checkout ships them.

:func:`select_engine` picks the repo engine when ``EEIK_ENGINE_PATH`` points at a valid checkout, else
the vendored one — so onboarding "always uses the real engine" when it is available, and degrades safely
when it is not.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

from . import capability_resolver as vendored
from .capability_resolver import Resolution, ResolvedPack
from .manifest import ProjectManifest

_log = get_logger("apex.eeik_engine")


@runtime_checkable
class EeikEngine(Protocol):
    """Resolves a manifest to a :class:`Resolution`. ``source`` labels the provenance."""

    source: str

    def resolve(self, manifest: ProjectManifest) -> Resolution: ...


class VendoredEeikEngine:
    """Resolver over the vendored ``eeik_assets/`` snapshot (delegates to ``capability_resolver``)."""

    source = "vendored"

    def resolve(self, manifest: ProjectManifest) -> Resolution:
        return vendored.resolve(manifest)


class RepoEeikEngine:
    """Resolver over a live eeik-bootstrap checkout, driven by each pack's ``manifest_triggers``."""

    def __init__(self, repo_path: str | Path) -> None:
        self._root = Path(repo_path)
        self._packs_dir = self._root / "capability-packs"
        if not self._packs_dir.is_dir():
            raise ValueError(f"no capability-packs/ under {self._root} — not an eeik-bootstrap checkout")
        self.source = f"repo:{self._root}"

    @functools.cached_property
    def _packs(self) -> list[dict[str, Any]]:
        packs: list[dict[str, Any]] = []
        for meta_path in sorted(self._packs_dir.glob("*/metadata.yaml")):
            data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
            name = data.get("name")
            if not name:
                continue
            packs.append(
                {
                    "name": name,
                    # A pack present in the checkout is built unless its metadata says otherwise.
                    "status": str(data.get("status", "built")),
                    "triggers": data.get("manifest_triggers", []) or [],
                    "agents": list(data.get("agents_provided", []) or []),
                    "category": str(data.get("category", "")),
                }
            )
        return packs

    def resolve(self, manifest: ProjectManifest) -> Resolution:
        flat = _flatten(manifest.model_dump())
        selected: list[dict[str, Any]] = []
        reasons: dict[str, list[str]] = {}

        for pack in self._packs:
            hit_reasons = _match_triggers(pack["triggers"], flat)
            if hit_reasons:
                selected.append(pack)
                reasons[pack["name"]] = hit_reasons

        # Deterministic order: core category first, then alphabetical by name.
        selected.sort(key=lambda p: (0 if p["category"] == "core" else 1, p["name"]))

        packs = [
            ResolvedPack(name=p["name"], availability=p["status"], selected_by=reasons[p["name"]])
            for p in selected
        ]
        agents: list[str] = []
        for p in selected:
            agents.extend(p["agents"])
        agents.append("code-reviewer")
        recommended_agents = list(dict.fromkeys(agents))

        gov = manifest.governance
        governance_required = bool(
            manifest.ai.governance_required
            or gov.profile in {"regulated", "enterprise"}
            or any(p["name"] == "governance-pack" for p in selected)
        )
        return Resolution(
            packs=packs,
            reviews_required=list(gov.reviews_required),
            compliance_hints=list(gov.compliance_frameworks),
            recommended_agents=recommended_agents,
            governance_required=governance_required,
        )


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten a nested manifest dict to dotted keys (``technology.backend.language`` → value)."""
    flat: dict[str, Any] = {}
    for key, value in data.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, prefix=f"{dotted}."))
        else:
            flat[dotted] = value
    return flat


def _match_triggers(triggers: list[dict[str, Any]], flat: dict[str, Any]) -> list[str]:
    """Return the human-readable reasons a pack's triggers match the manifest (empty = no match)."""
    reasons: list[str] = []
    for trigger in triggers:
        if not isinstance(trigger, dict):
            continue  # tolerate packs whose triggers use a shorthand shape
        field = trigger.get("field")
        # eeik packs use either ``values: [..]`` (list) or ``value: x`` (scalar).
        values = trigger.get("values")
        if values is None:
            values = [trigger["value"]] if "value" in trigger else []
        if field is None or field not in flat:
            continue
        actual = flat[field]
        candidates = actual if isinstance(actual, list) else [actual]
        for cand in candidates:
            if cand in values or (isinstance(cand, bool) and cand and True in values):
                reasons.append(f"{field}={cand}")
                break
    return reasons


def select_engine(settings: Settings | None = None) -> EeikEngine:
    """Return the repo engine when ``EEIK_ENGINE_PATH`` is a valid checkout, else the vendored engine."""
    settings = settings or get_settings()
    path = settings.EEIK_ENGINE_PATH.strip()
    if path:
        try:
            engine = RepoEeikEngine(path)
            _log.info("eeik_engine.selected", source=engine.source)
            return engine
        except ValueError as exc:
            _log.warning("eeik_engine.repo_invalid", path=path, error=str(exc))
    return VendoredEeikEngine()
