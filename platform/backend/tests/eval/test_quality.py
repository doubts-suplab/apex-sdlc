"""Artifact quality-eval harness tests (closes Increment 5's offline tail)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.agents.orchestrator import run_reference_journey
from app.eval import evaluate_artifact, evaluate_artifacts
from app.integrations.llm.stub_provider import StubLLMProvider


def test_reference_journey_scores_high_with_no_flags() -> None:
    journey = run_reference_journey(StubLLMProvider())
    artifacts = [a for p in journey.phases for a in p.artifacts]
    result = evaluate_artifacts(artifacts)
    assert len(result.artifacts) == 17
    assert result.mean_score > 0.9
    assert result.flagged == []  # the deterministic reference set is clean


def test_empty_artifact_is_flagged() -> None:
    ev = evaluate_artifact({"name": "blank.md", "kind": "md", "content": "   "})
    assert ev.flagged is True
    assert any(c.name == "non_empty" and not c.passed for c in ev.checks)


def test_placeholder_artifact_is_flagged() -> None:
    ev = evaluate_artifact(
        {"name": "draft.md", "kind": "md", "content": "# Title\n\nTODO: write this section later."}
    )
    assert any(c.name == "no_placeholder" and not c.passed for c in ev.checks)


def test_gherkin_structure_check() -> None:
    good = evaluate_artifact(
        {
            "name": "s.md",
            "kind": "gherkin",
            "content": "# S\n\nFeature: X\nScenario: Y\nGiven a\nWhen b\nThen c",
        }
    )
    assert any(c.name == "gherkin_structure" and c.passed for c in good.checks)
    bad = evaluate_artifact(
        {"name": "s.md", "kind": "gherkin", "content": "# S\n\nFeature: X only, no scenarios."}
    )
    assert any(c.name == "gherkin_structure" and not c.passed for c in bad.checks)


def test_adr_structure_check() -> None:
    ev = evaluate_artifact(
        {
            "name": "ADR-0001.md",
            "kind": "adr",
            "content": "# ADR-0001\n\n## Context\nc\n\n## Decision\nd\n\n## Consequences\ne",
        }
    )
    assert any(c.name == "adr_structure" and c.passed for c in ev.checks)


@pytest.mark.asyncio
async def test_reference_quality_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/journey/reference/quality")
    assert resp.status_code == 200
    data = resp.json()
    assert data["artifact_count"] == 17
    assert data["all_pass"] is True
    assert data["mean_score"] > 0.9
