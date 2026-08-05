"""Resolve an eeik project manifest to its capability packs — deterministically, offline.

Implements the resolution rules documented at the top of ``eeik_assets/capability-matrix.yaml``: collect
packs from every matching manifest field, dedupe, and order by the matrix's ``resolution_order``. Pure
functions over vendored data — no LLM, no network.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .manifest import ProjectManifest

_ASSETS = Path(__file__).parent / "eeik_assets"
_MATRIX_PATH = _ASSETS / "capability-matrix.yaml"

# Pack availability, transcribed from the capability-matrix.yaml inline markers (YAML strips comments,
# so this is maintained alongside the vendored file — see eeik_assets/PROVENANCE.md).
_AVAILABILITY: dict[str, str] = {
    "architecture-pack": "built",
    "java-pack": "built",
    "aws-pack": "built",
    "ai-engineering-pack": "built",
    "agent-harness-pack": "built",
    "governance-pack": "built",
    "modernization-pack": "built",
    "python-pack": "built",
    "react-pack": "built",
    "angular-pack": "built",
    "insurance-pack": "built",
    "banking-pack": "built",
    "healthcare-pack": "built",
    # Still on the eeik roadmap (ROADMAP v2.0) — not yet in capability-packs/.
    "azure-pack": "planned",
    "gcp-pack": "planned",
    "retail-pack": "planned",
}

# Primary eeik agent per pack — a derived hint for the scaffold's "recommended agents".
_PACK_AGENTS: dict[str, tuple[str, ...]] = {
    "architecture-pack": ("architect",),
    "java-pack": ("java-developer", "java-tech-lead", "java-tester"),
    "python-pack": ("python-developer",),
    "aws-pack": ("aws-architect",),
    "ai-engineering-pack": ("ai-engineer",),
    "agent-harness-pack": ("ai-engineer",),
    "governance-pack": ("security-auditor",),
    "react-pack": ("react-developer",),
    "angular-pack": ("angular-developer",),
    "modernization-pack": ("modernization-expert",),
}


@dataclass
class ResolvedPack:
    name: str
    availability: str  # "built" | "stub" | "planned"
    selected_by: list[str] = field(default_factory=list)


@dataclass
class Resolution:
    """The full outcome of resolving a manifest against the capability matrix."""

    packs: list[ResolvedPack]
    reviews_required: list[str]
    compliance_hints: list[str]
    recommended_agents: list[str]
    governance_required: bool

    def pack_names(self) -> list[str]:
        return [p.name for p in self.packs]


@functools.lru_cache(maxsize=1)
def load_matrix() -> dict[str, Any]:
    """Parse the vendored capability matrix (cached)."""
    return yaml.safe_load(_MATRIX_PATH.read_text(encoding="utf-8"))


def _section_packs(section: dict[str, Any] | None, key: str) -> list[str]:
    if not section:
        return []
    entry = section.get(key) or {}
    return list(entry.get("packs", []))


def resolve(manifest: ProjectManifest) -> Resolution:
    """Resolve a manifest to ordered capability packs + reviews, agents, and governance flags."""
    matrix = load_matrix()
    selections: dict[str, list[str]] = {}  # pack -> manifest fields that selected it
    reviews: list[str] = []
    compliance: list[str] = []
    agents: list[str] = []

    def add(packs: list[str], reason: str) -> None:
        for pack in packs:
            selections.setdefault(pack, [])
            if reason not in selections[pack]:
                selections[pack].append(reason)

    # project_type extra packs (resolved first) + governance override.
    pt = (matrix.get("project_type") or {}).get(manifest.project.project_type) or {}
    add(list(pt.get("extra_packs", [])), f"project_type={manifest.project.project_type}")
    gov_profile = pt.get("governance_override", manifest.governance.profile)

    add(_section_packs(matrix.get("backend"), manifest.technology.backend.language),
        f"backend={manifest.technology.backend.language}")
    add(_section_packs(matrix.get("frontend"), manifest.technology.frontend.framework),
        f"frontend={manifest.technology.frontend.framework}")
    add(_section_packs(matrix.get("cloud"), manifest.cloud.provider), f"cloud={manifest.cloud.provider}")
    add(_section_packs(matrix.get("architecture"), manifest.architecture.style),
        f"architecture={manifest.architecture.style}")
    if manifest.ai.enabled:
        add(_section_packs(matrix.get("ai"), manifest.ai.pattern), f"ai={manifest.ai.pattern}")

    gov_entry = (matrix.get("governance") or {}).get(gov_profile) or {}
    add(list(gov_entry.get("packs", [])), f"governance={gov_profile}")
    reviews = list(gov_entry.get("reviews", [])) or list(manifest.governance.reviews_required)

    domain_entry = (matrix.get("domain") or {}).get(manifest.project.domain) or {}
    add(list(domain_entry.get("packs", [])), f"domain={manifest.project.domain}")
    compliance = list(domain_entry.get("compliance_hints", []))

    mod = manifest.modernization.source_platform
    if mod and mod != "none":
        mod_entry = (matrix.get("modernization") or {}).get(mod) or {}
        add(list(mod_entry.get("packs", [])), f"modernization={mod}")
        agents.extend(mod_entry.get("agents", []))

    # Order by the matrix's resolution_order (unlisted packs sort last, alphabetically).
    order_map = {name: n for n, name in (matrix.get("resolution_order") or {}).items()}
    ordered = sorted(selections, key=lambda p: (order_map.get(p, 999), p))

    packs = [
        ResolvedPack(name=p, availability=_AVAILABILITY.get(p, "planned"), selected_by=selections[p])
        for p in ordered
    ]

    # Recommended agents: derived per-pack + any modernization agents + a universal reviewer.
    for pack in ordered:
        agents.extend(_PACK_AGENTS.get(pack, ()))
    agents.append("code-reviewer")
    recommended_agents = list(dict.fromkeys(agents))  # dedupe, preserve order

    return Resolution(
        packs=packs,
        reviews_required=reviews,
        compliance_hints=compliance,
        recommended_agents=recommended_agents,
        governance_required=_governance_required(manifest, gov_profile, matrix),
    )


def resolve_packs(manifest: ProjectManifest) -> list[ResolvedPack]:
    """Convenience: just the ordered resolved packs."""
    return resolve(manifest).packs


def _governance_required(manifest: ProjectManifest, gov_profile: str, matrix: dict[str, Any]) -> bool:
    if manifest.ai.governance_required:
        return True
    for trigger in matrix.get("ai_governance_triggers", []):
        if manifest.project.domain in trigger.get("domain", []):
            return True
        if gov_profile in trigger.get("governance_profile", []):
            return True
        if manifest.ai.enabled and manifest.ai.pattern in trigger.get("ai_pattern", []):
            return True
    return False
