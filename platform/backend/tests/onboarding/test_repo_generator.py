"""Repo-tree emission tests — stack-appropriate, deterministic file trees + the bootstrap plan.

Self-contained: ``pytest --noconftest tests/onboarding/test_repo_generator.py``.
"""

from __future__ import annotations

from app.onboarding.manifest import ProjectManifest
from app.onboarding.repo_bootstrap import bootstrap_plan
from app.onboarding.repo_generator import generate_repo_tree
from app.onboarding.service import onboard

_BASE = {
    "schema_version": "1.0",
    "project": {"name": "Refund Service", "description": "Self-serve refunds", "owner": "pay",
                "domain": "banking", "project_type": "greenfield"},
    "architecture": {"style": "microservices"},
    "cloud": {"provider": "aws", "infra_as_code": "cdk"},
    "ai": {"enabled": False, "pattern": "none"},
    "governance": {"profile": "regulated"},
}


def _tree(backend: str, framework: str, frontend: str = "none") -> dict[str, str]:
    manifest = ProjectManifest.from_dict(
        {**_BASE, "technology": {"backend": {"language": backend, "framework": framework},
                                 "frontend": {"framework": frontend}}}
    )
    return generate_repo_tree(onboard(manifest), manifest)


def test_common_files_always_present():
    tree = _tree("python", "fastapi")
    for path in ("CLAUDE.md", "README.md", ".gitignore", ".github/workflows/ci.yml",
                 "project-manifest.yaml"):
        assert path in tree and tree[path]  # present and non-empty (except intentional .gitkeep)


def test_java_skeleton_is_compilable_shaped():
    tree = _tree("java", "spring-boot", frontend="react")
    assert "pom.xml" in tree and "spring-boot-starter-parent" in tree["pom.xml"]
    main = next(p for p in tree if p.endswith("Application.java"))
    assert "@SpringBootApplication" in tree[main]
    # DDD layer directories are laid down.
    assert any("/domain/.gitkeep" in p for p in tree)
    assert "frontend/package.json" in tree  # frontend requested
    assert "infra/README.md" in tree  # cdk requested


def test_python_skeleton_has_app_and_tests():
    tree = _tree("python", "fastapi")
    assert "pyproject.toml" in tree and "fastapi" in tree["pyproject.toml"]
    assert "@app.get" in tree["app/main.py"]
    assert "tests/test_health.py" in tree
    assert "pom.xml" not in tree  # not a java project


def test_emission_is_deterministic():
    assert _tree("java", "spring-boot") == _tree("java", "spring-boot")


def test_bootstrap_plan_shape():
    tree = _tree("python", "fastapi")
    plan = bootstrap_plan("acme", "refund-service", tree)
    assert plan["full_name"] == "acme/refund-service"
    assert plan["file_count"] == len(tree)
    assert plan["executed"] is False and sorted(plan["files"]) == plan["files"]
