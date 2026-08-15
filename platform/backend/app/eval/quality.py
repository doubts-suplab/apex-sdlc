"""Artifact quality-eval harness — rubric scoring of a generated artifact's substance.

The generation path (``PhaseAgent.generate``) already fails safe: a short/empty/failed LLM reply
falls back to a deterministic template, so an artifact is never silently blank. This module is the
*measurement* side: it scores each artifact against a transparent rubric — structural checks that
apply to every artifact plus kind-specific ones — and flags anything degenerate (empty,
placeholder-laden, or missing the structure its kind requires).

Pure and deterministic: it reads only the artifact's own text, so the offline reference journey
scores identically every run, and a real provider's output can be measured with the same yardstick.
The rubric is intentionally simple and legible — a quality *signal*, not an LLM-judge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# An artifact shorter than this reads as degenerate (a blank or one-liner), not a real spec.
_MIN_NON_EMPTY = 40
# Below this a substantive artifact is suspiciously terse for its kind (a weak/failed generation).
_SUBSTANTIVE_LEN = 120
# Score at or above which an artifact is considered acceptable; below it is flagged for review.
_FLAG_THRESHOLD = 0.75

# Placeholder / unresolved-template markers that should never survive into a finished artifact.
_PLACEHOLDER = re.compile(
    r"\b(TODO|FIXME|TBD|XXX|lorem ipsum|placeholder|UNSET)\b|\{\{", re.IGNORECASE
)
_HEADING = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_MERMAID_KW = re.compile(
    r"\b(graph|flowchart|sequenceDiagram|classDiagram|erDiagram|stateDiagram|C4\w*)\b"
)


@dataclass(frozen=True)
class CheckResult:
    """One rubric check applied to an artifact."""

    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass
class ArtifactEval:
    """The quality outcome for a single artifact: its checks, a 0–1 score, and a flag."""

    name: str
    kind: str
    score: float
    flagged: bool
    checks: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "score": round(self.score, 3),
            "flagged": self.flagged,
            "checks": [c.to_dict() for c in self.checks],
        }


@dataclass
class JourneyEval:
    """Aggregate quality across a set of artifacts."""

    artifacts: list[ArtifactEval]
    mean_score: float
    flagged: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_count": len(self.artifacts),
            "mean_score": round(self.mean_score, 3),
            "flagged_count": len(self.flagged),
            "flagged": self.flagged,
            "all_pass": not self.flagged,
            "artifacts": [a.to_dict() for a in self.artifacts],
        }


def _kind_of(artifact: dict[str, Any]) -> str:
    return str(artifact.get("kind", "")).lower()


def _structural_checks(content: str) -> list[CheckResult]:
    stripped = content.strip()
    return [
        CheckResult("non_empty", len(stripped) >= _MIN_NON_EMPTY, f"{len(stripped)} chars"),
        CheckResult("substantive", len(stripped) >= _SUBSTANTIVE_LEN, f"{len(stripped)} chars"),
        CheckResult("has_heading", bool(_HEADING.search(content)), "markdown heading present"),
        CheckResult(
            "no_placeholder",
            not _PLACEHOLDER.search(content),
            "no TODO/TBD/placeholder/unresolved-template markers",
        ),
    ]


def _kind_checks(artifact: dict[str, Any], content: str) -> list[CheckResult]:
    kind = _kind_of(artifact)
    name = str(artifact.get("name", "")).lower()
    checks: list[CheckResult] = []
    if kind == "gherkin" or "feature:" in content.lower():
        ok = "Feature:" in content and "Scenario:" in content and any(
            k in content for k in ("Given", "When", "Then")
        )
        checks.append(CheckResult("gherkin_structure", ok, "Feature + Scenario + Given/When/Then"))
    if kind == "adr" or "adr" in name:
        ok = "Decision" in content and ("Consequences" in content or "Context" in content)
        checks.append(CheckResult("adr_structure", ok, "Decision + Context/Consequences"))
    if kind == "mermaid" or name.endswith(".mmd"):
        has_diagram = bool(_MERMAID_KW.search(content))
        checks.append(CheckResult("mermaid_diagram", has_diagram, "diagram declaration present"))
    return checks


def evaluate_artifact(artifact: dict[str, Any]) -> ArtifactEval:
    """Score one artifact against the structural + kind-specific rubric."""
    content = str(artifact.get("content", ""))
    checks = _structural_checks(content) + _kind_checks(artifact, content)
    passed = sum(1 for c in checks if c.passed)
    score = passed / len(checks) if checks else 0.0
    non_empty_ok = next((c.passed for c in checks if c.name == "non_empty"), True)
    # A degenerate (empty) artifact is always flagged regardless of the ratio.
    flagged = score < _FLAG_THRESHOLD or not non_empty_ok
    return ArtifactEval(
        name=str(artifact.get("name", "")),
        kind=str(artifact.get("kind", "")),
        score=score,
        flagged=flagged,
        checks=checks,
    )


def evaluate_artifacts(artifacts: list[dict[str, Any]]) -> JourneyEval:
    """Evaluate every artifact and aggregate (mean score + the flagged set)."""
    evals = [evaluate_artifact(a) for a in artifacts]
    mean = sum(e.score for e in evals) / len(evals) if evals else 0.0
    flagged = [e.name for e in evals if e.flagged]
    return JourneyEval(artifacts=evals, mean_score=mean, flagged=flagged)
