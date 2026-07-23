"""The APEX persona / phase / agent catalog — the single source of truth.

Every other place that describes "which persona owns which phase, run by which agent, producing which
artifacts, at what authority" derives from this module:

- the orchestrator (``orchestrator.py``) iterates ``PHASE_CATALOG`` in order;
- the journey API (``api/v1/journey.py``) serialises it;
- ``docs/personas.md`` and the frontend ``types/journey.ts`` mirror it (keep them in sync).

Authority levels come straight from the agent classes (a phase's authority IS its agent's
``authority_level``) so this catalog can never drift from the governed behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_harness import AuthorityLevel

from .architecture import ArchitectureAgent
from .base import PhaseAgent
from .cicd import ReleaseEngineerAgent
from .compliance import ComplianceOfficerAgent
from .development import PRReviewerAgent
from .docs import TechWriterAgent
from .requirements import RequirementsAgent
from .testing import QAAnalystAgent

# Persona keys — mirror frontend types/project.ts PersonaSchema.
PERSONAS: tuple[str, ...] = ("developer", "ba", "qa", "pm", "lead", "architect", "ciso")

# Phase keys — mirror frontend types/project.ts PhaseTypeSchema and PHASE_ORDER.
PHASE_ORDER: tuple[str, ...] = (
    "requirements",
    "architecture",
    "development",
    "testing",
    "cicd",
    "docs",
    "governance",
)


@dataclass(frozen=True)
class PhaseSpec:
    """One SDLC phase: its owning persona, the agent that runs it, and what it produces."""

    phase: str
    label: str
    agent_cls: type[PhaseAgent]
    primary_persona: str
    stakeholders: tuple[str, ...]  # personas who contribute to or consume this phase
    artifacts: tuple[str, ...]
    destinations: tuple[str, ...]
    eeik_agent: str
    summary: str = field(default="")

    @property
    def agent_name(self) -> str:
        return self.agent_cls.name

    @property
    def authority(self) -> AuthorityLevel:
        return self.agent_cls.authority_level

    @property
    def auto_enforces(self) -> bool:
        """True if this phase's authority can ever auto-enforce (SUGGEST/OBSERVE never can — gate G-5)."""
        return self.authority > AuthorityLevel.SUGGEST


PHASE_CATALOG: tuple[PhaseSpec, ...] = (
    PhaseSpec(
        phase="requirements",
        label="Requirements",
        agent_cls=RequirementsAgent,
        primary_persona="ba",
        stakeholders=("ba", "pm", "architect"),
        artifacts=("user-stories.md", "gap-analysis.md"),
        destinations=("Jira", "Confluence", "artifact-db"),
        eeik_agent="business-analyst",
        summary="BA turns the brief into Gherkin stories + a gap analysis; a human approves.",
    ),
    PhaseSpec(
        phase="architecture",
        label="Architecture",
        agent_cls=ArchitectureAgent,
        primary_persona="architect",
        stakeholders=("architect", "lead", "developer"),
        artifacts=("ADR-0001-refund-service.md", "component-diagram.mmd", "tech-debt.md"),
        destinations=("Confluence", "repo", "artifact-db"),
        eeik_agent="architect",
        summary="Architect proposes an ADR + component diagram; a human signs it off.",
    ),
    PhaseSpec(
        phase="development",
        label="Development",
        agent_cls=PRReviewerAgent,
        primary_persona="developer",
        stakeholders=("developer", "lead"),
        artifacts=("pr-review.md", "quality-report.md"),
        destinations=("GitHub", "artifact-db"),
        eeik_agent="code-reviewer",
        summary="PR reviewer flags issues (advisory ALERT); a human still merges.",
    ),
    PhaseSpec(
        phase="testing",
        label="Testing",
        agent_cls=QAAnalystAgent,
        primary_persona="qa",
        stakeholders=("qa", "developer"),
        artifacts=("test-plan.md", "test-cases.md", "coverage-gaps.md"),
        destinations=("Confluence", "Jira", "artifact-db"),
        eeik_agent="tester",
        summary="QA drafts a test plan + BDD cases + coverage gaps; a human approves.",
    ),
    PhaseSpec(
        phase="cicd",
        label="CI/CD",
        agent_cls=ReleaseEngineerAgent,
        primary_persona="lead",
        stakeholders=("lead", "developer"),
        artifacts=("release-notes.md", "deployment-checklist.md", "rollback-plan.md"),
        destinations=("GitHub", "Confluence", "artifact-db"),
        eeik_agent="ci-engineer",
        summary="Release engineer assembles release artifacts; auto-approves when checks are green.",
    ),
    PhaseSpec(
        phase="docs",
        label="Docs",
        agent_cls=TechWriterAgent,
        primary_persona="developer",
        stakeholders=("developer", "ba"),
        artifacts=("api-reference.md", "onboarding-guide.md"),
        destinations=("Confluence", "repo", "artifact-db"),
        eeik_agent="technical-writer",
        summary="Technical writer drafts API + onboarding docs; a human publishes.",
    ),
    PhaseSpec(
        phase="governance",
        label="Governance",
        agent_cls=ComplianceOfficerAgent,
        primary_persona="ciso",
        stakeholders=("ciso", "lead", "architect"),
        artifacts=("governance-report.md", "risk-register.md"),
        destinations=("Confluence", "CISO-view", "artifact-db"),
        eeik_agent="security-auditor",
        summary="Compliance officer assesses risk; a confident material breach can auto-block.",
    ),
)

_BY_PHASE: dict[str, PhaseSpec] = {spec.phase: spec for spec in PHASE_CATALOG}


def spec_for(phase: str) -> PhaseSpec:
    """Return the PhaseSpec for a phase key, or raise KeyError if unknown."""
    return _BY_PHASE[phase]


def phases_for_persona(persona: str) -> tuple[PhaseSpec, ...]:
    """Phases a persona owns or contributes to/consumes (for the per-persona journey view)."""
    return tuple(s for s in PHASE_CATALOG if persona == s.primary_persona or persona in s.stakeholders)
