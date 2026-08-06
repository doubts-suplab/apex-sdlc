"""Repo-generation demo — emit a full scaffolded repository from an eeik manifest, offline.

    python -m app.demo.generate_repo [example-name]

Onboards an eeik example manifest, emits the **actual repository file tree** (not just a plan) under
``examples/generated-repo/<slug>/``, and prints a GitHub bootstrap dry-run. Deterministic, no network —
the emitted repo is byte-reproducible.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from app.onboarding.manifest import ProjectManifest
from app.onboarding.repo_bootstrap import bootstrap_plan
from app.onboarding.repo_generator import generate_repo_tree
from app.onboarding.service import onboard

_REPO_ROOT = Path(__file__).resolve().parents[4]
_ASSETS = Path(__file__).resolve().parents[1] / "onboarding" / "eeik_assets" / "examples"
_OUT = _REPO_ROOT / "examples" / "generated-repo"
_DEFAULT_EXAMPLE = "greenfield-java-aws"


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    example = argv[0] if argv else _DEFAULT_EXAMPLE
    manifest_path = _ASSETS / f"{example}.yaml"
    if not manifest_path.exists():
        print(f"ERROR: no example manifest {manifest_path}", file=sys.stderr)
        return 1

    manifest = ProjectManifest.from_dict(yaml.safe_load(manifest_path.read_text(encoding="utf-8")))
    result = onboard(manifest)
    tree = generate_repo_tree(result, manifest)

    from app.onboarding.repo_generator import _slug

    slug = _slug(manifest.project.name)
    out_dir = _OUT / slug
    for path, content in tree.items():
        target = out_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    plan = bootstrap_plan(manifest.project.owner or "acme", slug, tree)
    (out_dir / "_bootstrap-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    print(f"Emitted {len(tree)} files under {out_dir}")
    print(f"GitHub bootstrap (dry-run): would create {plan['full_name']} with {plan['file_count']} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
