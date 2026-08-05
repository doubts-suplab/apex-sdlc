"""Onboarding front-door tests — deterministic, self-contained (no DB / FastAPI).

Run with ``pytest --noconftest tests/onboarding/test_onboarding.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.onboarding.capability_resolver import resolve
from app.onboarding.manifest import ProjectManifest
from app.onboarding.questions import load_questions
from app.onboarding.service import ENTRY_PHASE, onboard, registration_payload

_EXAMPLES = Path(__file__).resolve().parents[1].parent / "app" / "onboarding" / "eeik_assets" / "examples"


def _load(example: str) -> ProjectManifest:
    return ProjectManifest.from_dict(yaml.safe_load((_EXAMPLES / f"{example}.yaml").read_text()))


# -- capability resolution follows the matrix ----------------------------------------------------
def test_greenfield_resolves_expected_packs():
    res = resolve(_load("greenfield-java-aws"))
    # Java + AWS + standard governance greenfield → these four, in resolution_order.
    assert res.pack_names() == ["architecture-pack", "java-pack", "aws-pack", "governance-pack"]
    assert all(p.availability == "built" for p in res.packs)
    assert res.governance_required is False
    assert res.reviews_required == ["architecture-review", "security-review"]


def test_agentic_poc_pulls_ai_packs_and_triggers_governance():
    res = resolve(_load("poc-ai-agent"))
    names = res.pack_names()
    assert "ai-engineering-pack" in names and "agent-harness-pack" in names
    # multi-agent AI trigger → governance required even though the profile is 'basic'.
    assert res.governance_required is True
    # every pack this manifest resolves is built as of eeik v1.4 (python-pack included).
    assert all(p.availability == "built" for p in res.packs)


def test_availability_tags_still_flag_planned_packs():
    # The resolver surfaces packs with an availability tag rather than hiding unbuilt ones.
    # azure/gcp/retail remain on the eeik roadmap (ROADMAP v2.0) → tagged 'planned'.
    from app.onboarding.capability_resolver import _AVAILABILITY

    assert _AVAILABILITY["azure-pack"] == "planned"
    assert _AVAILABILITY["retail-pack"] == "planned"
    assert _AVAILABILITY["python-pack"] == "built"


def test_resolution_is_ordered_and_deduped():
    res = resolve(_load("poc-ai-agent"))
    names = res.pack_names()
    assert names == list(dict.fromkeys(names))  # no dupes
    assert names.index("architecture-pack") < names.index("governance-pack")  # order preserved


# -- onboarding produces scaffold + registry hand-off --------------------------------------------
def test_onboard_produces_scaffold_files_and_enters_requirements():
    result = onboard(_load("greenfield-java-aws"))
    assert result.entry_phase == ENTRY_PHASE == "requirements"
    files = result.files()
    assert set(files) == {"CLAUDE.md", "project-manifest.yaml", "scaffold-plan.md"}
    assert "payment-gateway" in files["CLAUDE.md"]
    assert "architecture-pack" in files["scaffold-plan.md"]
    # normalized manifest round-trips as YAML.
    assert yaml.safe_load(files["project-manifest.yaml"])["project"]["name"] == "payment-gateway"


def test_registration_payload_maps_stack_to_apex_type():
    reg = registration_payload(onboard(_load("greenfield-java-aws")))
    assert reg["current_phase"] == "requirements"
    assert reg["status"] == "active"
    assert reg["slug"] == "payment-gateway"
    assert reg["project_type"] == "spring-boot"  # spring-boot backend → apex spring-boot type


def test_onboard_accepts_raw_dict():
    raw = yaml.safe_load((_EXAMPLES / "poc-ai-agent.yaml").read_text())
    result = onboard(raw)  # dict path, not a ProjectManifest
    assert result.project_name == "knowledge-agent-poc"


# -- validation ----------------------------------------------------------------------------------
def test_invalid_manifest_is_rejected():
    with pytest.raises(Exception):
        ProjectManifest.from_dict({"schema_version": "1.0"})  # missing required project/technology/…


# -- questions -----------------------------------------------------------------------------------
def test_questions_load_in_order():
    qs = load_questions()
    ids = [q.get("question_id") for q in qs]
    assert "project_type" in ids
    assert ids[0] == "project_type"  # project-type leads the wizard
    assert len(qs) >= 8
