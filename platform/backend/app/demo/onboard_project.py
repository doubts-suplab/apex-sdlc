"""Onboarding demo — onboard an eeik example project through the front door, offline.

    python -m app.demo.onboard_project [example-name]

Loads an eeik example manifest (default: greenfield-java-aws), runs the onboarding front door, writes the
scaffold (`CLAUDE.md`, `project-manifest.yaml`, `scaffold-plan.md`) to ``examples/onboarded-project/`` and
a `registration.json`, and prints a summary. No DB / network / API keys. Mirrors
``app.demo.reference_journey``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from app.onboarding.manifest import ProjectManifest
from app.onboarding.service import onboard, registration_payload

# app/demo/onboard_project.py → parents: demo, app, backend, platform, <repo root>
_REPO_ROOT = Path(__file__).resolve().parents[4]
_ASSETS = Path(__file__).resolve().parents[1] / "onboarding" / "eeik_assets" / "examples"
_DEFAULT_OUT = _REPO_ROOT / "examples" / "onboarded-project"
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
    reg = registration_payload(result)

    out_dir = _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in result.files().items():
        (out_dir / name).write_text(content, encoding="utf-8")
    (out_dir / "registration.json").write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")

    print(f"\nAPEX onboarding — {result.project_name} (from eeik example '{example}')")
    print("=" * 68)
    print(f"Project type : {reg['project_type']}   →   entry phase: {result.entry_phase}")
    print("Capability packs:")
    for p in result.packs:
        print(f"  - {p['name']:<22} ({p['availability']})")
    print(f"Governance required: {'yes' if result.governance_required else 'no'}"
          f"   reviews: {', '.join(result.reviews_required) or 'none'}")
    print(f"Recommended agents : {', '.join(result.recommended_agents)}")
    print(f"\nWrote {len(result.files()) + 1} files under {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
