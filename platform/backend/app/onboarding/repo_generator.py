"""Repository-tree emission — the compilable scaffold behind Phase 0's onboarding.

Turns an :class:`OnboardingResult` into an actual **file tree** (path → content), not just a plan: a
stack-appropriate skeleton (Java/Spring Boot or Python/FastAPI), `CLAUDE.md`, the normalized manifest, a
README, CI, and `.gitignore`. Pure and deterministic — no timestamps, no network — so the emitted repo is
byte-reproducible and committable as a golden example. This is the offline stand-in for eeik's LLM-driven
`repository-generator`; a live build can post the same tree to a new GitHub repo (see ``repo_bootstrap``).
"""

from __future__ import annotations

import re

from .manifest import ProjectManifest
from .scaffold import OnboardingResult

_GITIGNORE = """\
# Build / deps
target/
dist/
build/
__pycache__/
*.py[cod]
.venv/
node_modules/
.next/

# Env / secrets
.env
.env.*
!.env.example

# IDE / OS
.idea/
.vscode/
.DS_Store
"""


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


def _java_package(slug: str) -> str:
    ident = re.sub(r"[^a-z0-9]", "", slug.lower()) or "app"
    return f"com.example.{ident}"


def _class_name(slug: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", slug)
    return "".join(p.capitalize() for p in parts if p) or "App"


def generate_repo_tree(result: OnboardingResult, manifest: ProjectManifest) -> dict[str, str]:
    """Return ``{path: content}`` for the scaffolded repository."""
    tree: dict[str, str] = {
        "CLAUDE.md": result.claude_md,
        "project-manifest.yaml": result.manifest_yaml,
        "README.md": _readme(result, manifest),
        ".gitignore": _GITIGNORE,
        ".github/workflows/ci.yml": _ci_workflow(manifest),
    }
    lang = manifest.technology.backend.language
    if lang in ("java", "mixed"):
        tree.update(_java_skeleton(manifest))
    if lang in ("python", "mixed"):
        tree.update(_python_skeleton(manifest))
    if manifest.technology.frontend.framework != "none":
        tree["frontend/package.json"] = _frontend_package_json(manifest)
    if manifest.cloud.infra_as_code in ("cdk", "terraform", "both"):
        tree["infra/README.md"] = (
            f"# Infrastructure ({manifest.cloud.infra_as_code})\n\n"
            f"Provision {manifest.project.name} on {manifest.cloud.provider} here.\n"
        )
    return dict(sorted(tree.items()))


def _readme(result: OnboardingResult, m: ProjectManifest) -> str:
    packs = "\n".join(f"- `{p['name']}` ({p['availability']})" for p in result.packs) or "- (none)"
    agents = ", ".join(f"`{a}`" for a in result.recommended_agents)
    return (
        f"# {m.project.name}\n\n"
        f"{m.project.description or 'Onboarded via the APEX / eeik front door.'}\n\n"
        f"- **Stack:** {m.technology.backend.language}"
        f"{' / ' + (m.technology.backend.framework or '') if m.technology.backend.framework else ''}\n"
        f"- **Architecture:** {m.architecture.style} · **Cloud:** {m.cloud.provider} "
        f"({m.cloud.infra_as_code})\n"
        f"- **Governance profile:** {m.governance.profile}\n\n"
        f"## Capability packs\n\n{packs}\n\n"
        f"## Recommended eeik agents\n\n{agents}\n\n"
        f"## SDLC\n\n"
        f"This project enters the APEX spec-driven spine at the **{result.entry_phase}** phase.\n"
    )


def _ci_workflow(m: ProjectManifest) -> str:
    lang = m.technology.backend.language
    if lang in ("java", "mixed"):
        steps = (
            "      - uses: actions/setup-java@v4\n"
            "        with:\n"
            "          distribution: temurin\n"
            "          java-version: '21'\n"
            "      - run: mvn -B verify\n"
        )
    else:
        steps = (
            "      - uses: actions/setup-python@v5\n"
            "        with:\n"
            "          python-version: '3.12'\n"
            "      - run: pip install -e '.[test]'\n"
            "      - run: pytest\n"
        )
    return (
        "name: CI\n\n"
        "on:\n  push:\n  pull_request:\n\n"
        "jobs:\n"
        "  build:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        f"{steps}"
    )


def _java_skeleton(m: ProjectManifest) -> dict[str, str]:
    pkg = _java_package(_slug(m.project.name))
    pkg_path = pkg.replace(".", "/")
    cls = _class_name(_slug(m.project.name))
    main = (
        f"package {pkg};\n\n"
        "import org.springframework.boot.SpringApplication;\n"
        "import org.springframework.boot.autoconfigure.SpringBootApplication;\n\n"
        "@SpringBootApplication\n"
        f"public class {cls}Application {{\n"
        "    public static void main(String[] args) {\n"
        f"        SpringApplication.run({cls}Application.class, args);\n"
        "    }\n"
        "}\n"
    )
    test = (
        f"package {pkg};\n\n"
        "import org.junit.jupiter.api.Test;\n"
        "import org.springframework.boot.test.context.SpringBootTest;\n\n"
        "@SpringBootTest\n"
        f"class {cls}ApplicationTests {{\n"
        "    @Test\n"
        "    void contextLoads() {}\n"
        "}\n"
    )
    return {
        "pom.xml": _pom_xml(m, pkg),
        f"src/main/java/{pkg_path}/web/{cls}Application.java": main,
        f"src/main/java/{pkg_path}/domain/.gitkeep": "",
        f"src/main/java/{pkg_path}/application/.gitkeep": "",
        f"src/main/java/{pkg_path}/infrastructure/.gitkeep": "",
        f"src/test/java/{pkg_path}/{cls}ApplicationTests.java": test,
    }


def _pom_xml(m: ProjectManifest, pkg: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
        "  <modelVersion>4.0.0</modelVersion>\n"
        "  <parent>\n"
        "    <groupId>org.springframework.boot</groupId>\n"
        "    <artifactId>spring-boot-starter-parent</artifactId>\n"
        "    <version>3.3.0</version>\n"
        "  </parent>\n"
        f"  <groupId>{pkg}</groupId>\n"
        f"  <artifactId>{_slug(m.project.name)}</artifactId>\n"
        "  <version>0.1.0</version>\n"
        "  <properties><java.version>21</java.version></properties>\n"
        "  <dependencies>\n"
        "    <dependency>\n"
        "      <groupId>org.springframework.boot</groupId>\n"
        "      <artifactId>spring-boot-starter-web</artifactId>\n"
        "    </dependency>\n"
        "    <dependency>\n"
        "      <groupId>org.springframework.boot</groupId>\n"
        "      <artifactId>spring-boot-starter-test</artifactId>\n"
        "      <scope>test</scope>\n"
        "    </dependency>\n"
        "  </dependencies>\n"
        "</project>\n"
    )


def _python_skeleton(m: ProjectManifest) -> dict[str, str]:
    tree = {
        "pyproject.toml": _pyproject(m),
        "app/__init__.py": "",
        "app/main.py": (
            "from fastapi import FastAPI\n\n"
            "app = FastAPI(title=" + repr(m.project.name) + ")\n\n\n"
            '@app.get("/health")\n'
            "async def health() -> dict[str, str]:\n"
            '    return {"status": "ok"}\n'
        ),
        "tests/__init__.py": "",
        "tests/test_health.py": (
            "from fastapi.testclient import TestClient\n"
            "from app.main import app\n\n\n"
            "def test_health():\n"
            "    assert TestClient(app).get(\"/health\").json() == {\"status\": \"ok\"}\n"
        ),
    }
    for layer in ("api", "core", "models", "services"):
        tree[f"app/{layer}/__init__.py"] = ""
    return tree


def _pyproject(m: ProjectManifest) -> str:
    return (
        "[project]\n"
        f'name = "{_slug(m.project.name)}"\n'
        'version = "0.1.0"\n'
        f'description = "{m.project.description or m.project.name}"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["fastapi>=0.115", "uvicorn>=0.30"]\n\n'
        "[project.optional-dependencies]\n"
        'test = ["pytest>=8", "httpx>=0.27"]\n\n'
        "[tool.ruff]\nline-length = 100\n"
    )


def _frontend_package_json(m: ProjectManifest) -> str:
    fw = m.technology.frontend.framework
    return (
        "{\n"
        f'  "name": "{_slug(m.project.name)}-frontend",\n'
        '  "version": "0.1.0",\n'
        '  "private": true,\n'
        f'  "description": "{fw} frontend for {m.project.name}",\n'
        '  "scripts": {"dev": "next dev", "build": "next build"}\n'
        "}\n"
    )
