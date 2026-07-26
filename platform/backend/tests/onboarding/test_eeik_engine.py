"""EEIK engine tests — vendored vs a real eeik-bootstrap checkout.

The repo engine is exercised against a synthetic checkout (hermetic) and, when a real eeik-bootstrap
checkout is present, an assertion that it sees packs the vendored snapshot still marks "planned".

Self-contained: ``pytest --noconftest tests/onboarding/test_eeik_engine.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.onboarding.eeik_engine import (
    RepoEeikEngine,
    VendoredEeikEngine,
    select_engine,
)
from app.onboarding.manifest import ProjectManifest

_MANIFEST = {
    "schema_version": "1.0",
    "project": {"name": "refund-service", "description": "", "owner": "pay",
                "domain": "banking", "project_type": "greenfield"},
    "technology": {"backend": {"language": "python", "framework": "fastapi"},
                   "frontend": {"framework": "react"}, "database": {"migration_tool": "alembic"}},
    "architecture": {"style": "microservices", "api_style": "rest"},
    "cloud": {"provider": "aws", "infra_as_code": "cdk"},
    "ai": {"enabled": False, "pattern": "none"},
    "governance": {"profile": "regulated"},
}


def _manifest() -> ProjectManifest:
    return ProjectManifest.from_dict(_MANIFEST)


def _write_pack(root: Path, name: str, *, triggers: list[dict], status: str | None = None,
                agents: list[str] | None = None, category: str = "") -> None:
    pack_dir = root / "capability-packs" / name.replace("-pack", "")
    pack_dir.mkdir(parents=True)
    meta: dict = {"name": name, "manifest_triggers": triggers, "category": category}
    if status:
        meta["status"] = status
    if agents:
        meta["agents_provided"] = agents
    (pack_dir / "metadata.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")


def _fake_checkout(tmp_path: Path) -> Path:
    _write_pack(tmp_path, "python-pack",
                triggers=[{"field": "technology.backend.language", "values": ["python"]}],
                agents=["python-developer"], category="language")
    _write_pack(tmp_path, "core-pack", triggers=[{"field": "project.project_type",
                "values": ["greenfield", "mvp"]}], category="core")
    _write_pack(tmp_path, "azure-pack",  # should NOT match (cloud is aws)
                triggers=[{"field": "cloud.provider", "values": ["azure"]}])
    return tmp_path


# -- repo engine over a synthetic checkout ------------------------------------------------------
def test_repo_engine_resolves_via_pack_triggers(tmp_path: Path):
    engine = RepoEeikEngine(_fake_checkout(tmp_path))
    res = engine.resolve(_manifest())
    names = res.pack_names()
    assert "python-pack" in names and "core-pack" in names
    assert "azure-pack" not in names  # cloud=aws, so the azure trigger did not fire
    # core category sorts first.
    assert names[0] == "core-pack"
    assert "python-developer" in res.recommended_agents
    assert engine.source.startswith("repo:")


def test_repo_engine_reports_presence_as_built(tmp_path: Path):
    engine = RepoEeikEngine(_fake_checkout(tmp_path))
    res = engine.resolve(_manifest())
    python = next(p for p in res.packs if p.name == "python-pack")
    assert python.availability == "built"  # present in the checkout → built


def test_invalid_checkout_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        RepoEeikEngine(tmp_path / "nope")


def test_select_engine_falls_back_to_vendored_for_bad_path():
    from app.core.config import Settings

    settings = Settings(DATABASE_URL="x", REDIS_URL="y", SECRET_KEY="z",  # type: ignore[arg-type]
                        EEIK_ENGINE_PATH="/does/not/exist")
    assert isinstance(select_engine(settings), VendoredEeikEngine)


# -- against the real eeik-bootstrap checkout, if present ----------------------------------------
_REAL_EEIK = Path("/home/user/eeik-bootstrap")


@pytest.mark.skipif(
    not (_REAL_EEIK / "capability-packs").is_dir(), reason="no real eeik-bootstrap checkout"
)
def test_real_repo_sees_packs_vendored_calls_planned():
    """The live repo ships python/react/banking packs the vendored snapshot still marks 'planned'."""
    repo = RepoEeikEngine(_REAL_EEIK).resolve(_manifest())
    vendored = VendoredEeikEngine().resolve(_manifest())
    repo_built = {p.name for p in repo.packs if p.availability == "built"}
    vendored_planned = {p.name for p in vendored.packs if p.availability == "planned"}
    # python-pack is 'planned' in the vendored matrix but built in the live checkout.
    assert "python-pack" in repo_built
    assert "python-pack" in vendored_planned
