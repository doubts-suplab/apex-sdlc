"""APEX onboarding — the eeik front door.

Deterministic, offline transform: an eeik project manifest → resolved capability packs → a scaffold
(project CLAUDE.md + normalized manifest + scaffold plan) → a project registered at the Requirements
phase, entering the spec-driven spine. No LLM, no network, no credentials.

eeik owns the source of truth (schema, questions, capability matrix); APEX vendors a copy of that data
under ``eeik_assets/`` (see ``eeik_assets/PROVENANCE.md``) so it can onboard standalone.
"""

from __future__ import annotations

from .capability_resolver import ResolvedPack, resolve_packs
from .manifest import ProjectManifest
from .scaffold import OnboardingResult, build_scaffold
from .service import onboard

__all__ = [
    "ProjectManifest",
    "ResolvedPack",
    "resolve_packs",
    "OnboardingResult",
    "build_scaffold",
    "onboard",
]
