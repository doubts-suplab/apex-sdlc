"""Demo — onboard an example project by consuming the REAL eeik engine (SDK, then MCP).

    python -m app.demo.eeik_engine_demo [example-name] [--mode sdk|mcp]

Instead of APEX's vendored offline path, this validates and resolves the manifest through the actual
eeik engine: in-process via the SDK (``import eeik``) and, as an option, over MCP (spawning ``eeik mcp``).
Requires the eeik package to be installed (``pip install -e ../../eeik-bootstrap``); MCP mode also needs
the ``mcp`` client. If eeik is unavailable the demo says so and exits cleanly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from app.onboarding import get_engine, onboard_with_eeik

_ASSETS = Path(__file__).resolve().parents[1] / "onboarding" / "eeik_assets" / "examples"
_DEFAULT_EXAMPLE = "greenfield-java-aws"


def _run_mode(manifest: dict, mode: str) -> None:
    engine = get_engine(mode)
    print(f"\n── mode: {mode} " + "─" * 50)
    if engine is None:
        print(f"  (unavailable — {mode} backend's dependencies are not installed; skipping)")
        return
    result, prov = onboard_with_eeik(manifest, engine=engine)
    print(f"  engine            : {prov['engine']}")
    print(f"  manifest valid    : {prov['validation']['valid']} "
          f"({len(prov['validation']['warnings'])} warning(s))")
    print(f"  eeik resolved packs: {', '.join(prov['eeik_resolved_packs'])}")
    print(f"  APEX project type : {result.manifest.get('project', {}).get('project_type', '?')} "
          f"→ entry phase '{result.entry_phase}'")
    verify = engine.verify()
    print(f"  eeik verify       : {'ok' if verify['ok'] else 'NON-CONFORMANT'} "
          f"({verify['counts']['warn']} warn, {verify['counts']['fail']} fail)")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    modes = ["sdk", "mcp"]
    if "--mode" in argv:
        i = argv.index("--mode")
        modes = [argv[i + 1]]
        argv = argv[:i] + argv[i + 2:]
    example = argv[0] if argv else _DEFAULT_EXAMPLE

    manifest_path = _ASSETS / f"{example}.yaml"
    if not manifest_path.exists():
        print(f"ERROR: no example manifest {manifest_path}", file=sys.stderr)
        return 1
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    print(f"APEX ⇄ EEIK engine — onboarding '{example}' by consuming the real eeik engine")
    print("=" * 72)
    if get_engine("sdk") is None:
        print("\neeik is not installed — `pip install -e ../../eeik-bootstrap` to enable SDK mode.")
        return 0
    for mode in modes:
        _run_mode(manifest, mode)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
