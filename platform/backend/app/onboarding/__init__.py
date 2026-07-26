"""APEX onboarding — the eeik front door.

Deterministic, offline transform: an eeik project manifest → resolved capability packs → a scaffold
(project CLAUDE.md + normalized manifest + scaffold plan) → a project registered at the Requirements
phase, entering the spec-driven spine. No LLM, no network, no credentials.

eeik owns the source of truth (schema, questions, capability matrix); APEX vendors a copy of that data
under ``eeik_assets/`` (see ``eeik_assets/PROVENANCE.md``) so it can onboard standalone.
"""

from __future__ import annotations

from .capability_resolver import ResolvedPack, resolve_packs
from .eeik_engine import EeikEngine, McpEngine, SdkEngine, get_engine
from .manifest import ProjectManifest
from .scaffold import OnboardingResult, build_scaffold
from .service import ManifestInvalidError, onboard, onboard_with_eeik

__all__ = [
    "ProjectManifest",
    "ResolvedPack",
    "resolve_packs",
    "OnboardingResult",
    "build_scaffold",
    "onboard",
    # Real eeik engine consumption (SDK in-process, or MCP over the protocol).
    "onboard_with_eeik",
    "ManifestInvalidError",
    "EeikEngine",
    "SdkEngine",
    "McpEngine",
    "get_engine",
]
