"""APEX consumes the real eeik engine — SDK (in-process) and MCP (over the protocol).

These tests require the eeik package to be importable (`pip install -e ../../eeik-bootstrap`); they
skip otherwise, so APEX's vendored offline path is never a hard dependency on eeik being present.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytest.importorskip("eeik", reason="eeik engine not installed")

from app.onboarding import (  # noqa: E402
    ManifestInvalidError,
    SdkEngine,
    get_engine,
    onboard_with_eeik,
)

_EXAMPLE = (
    Path(__file__).resolve().parents[2]
    / "app" / "onboarding" / "eeik_assets" / "examples" / "greenfield-java-aws.yaml"
)


@pytest.fixture
def manifest() -> dict:
    return yaml.safe_load(_EXAMPLE.read_text(encoding="utf-8"))


def test_get_engine_sdk_and_unknown():
    assert isinstance(get_engine("sdk"), SdkEngine)
    assert get_engine("bogus-mode") is None


def test_sdk_engine_validate_resolve_catalog_verify(manifest):
    engine = SdkEngine()
    v = engine.validate(manifest)
    assert v["valid"] is True and v["errors"] == []

    packs = engine.resolve_packs(manifest)
    assert "core" in packs and "java" in packs

    banking = engine.catalog(tag="banking")
    assert any(p["pack"] == "banking" for p in banking)

    report = engine.verify()
    assert report["ok"] is True and "counts" in report


def test_onboard_with_eeik_records_provenance(manifest):
    result, prov = onboard_with_eeik(manifest, mode="sdk")
    assert prov["engine"] == "sdk"
    assert prov["eeik_available"] is True
    assert prov["validation"]["valid"] is True
    assert "java" in prov["eeik_resolved_packs"]
    # the deterministic scaffold is still produced
    assert result.project_name and result.entry_phase == "requirements"


def test_onboard_with_eeik_rejects_invalid_manifest():
    with pytest.raises(ManifestInvalidError):
        onboard_with_eeik({"project": {"name": "x"}}, mode="sdk")


def test_onboard_falls_back_when_engine_unavailable(manifest):
    # An explicitly unavailable mode → vendored provenance, no eeik calls, scaffold still built.
    result, prov = onboard_with_eeik(manifest, mode="bogus-mode")
    assert prov["engine"] == "vendored" and prov["eeik_available"] is False
    assert prov["eeik_resolved_packs"] is None
    assert result.project_name


def test_mcp_engine_roundtrip(manifest):
    pytest.importorskip("mcp", reason="mcp client not installed")
    from app.onboarding import McpEngine

    try:
        engine = McpEngine()
        v = engine.validate(manifest)
    except Exception as exc:  # spawning `eeik mcp` unavailable in this environment
        pytest.skip(f"eeik MCP server not runnable here: {exc}")
    assert v["valid"] is True
    assert "java" in engine.resolve_packs(manifest)
