"""Reference-journey demo — run the Customer Refunds Service through every SDLC phase, offline.

    python -m app.demo.reference_journey

Constructs a deterministic stub LLM (no API key), runs the built-in reference project through the
governed harness for all seven phases, writes the generated artifacts to
``examples/reference-project/artifacts/<phase>/`` and a machine-readable ``journey.json`` beside them,
and prints a per-phase summary. This is the single command that regenerates the committed POC —
proof that the artifacts are produced by the governed harness, not hand-written.

No Postgres/Redis/S3/Anthropic/GitHub/Jira keys are required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.agents.orchestrator import JourneyResult, run_reference_journey
from app.integrations.llm.stub_provider import StubLLMProvider

# app/demo/reference_journey.py → parents: demo, app, backend, platform, <repo root>
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_OUT = _REPO_ROOT / "examples" / "reference-project"


def _write_artifacts(result: JourneyResult, out_dir: Path) -> int:
    artifacts_root = out_dir / "artifacts"
    written = 0
    for phase in result.phases:
        phase_dir = artifacts_root / phase.phase
        phase_dir.mkdir(parents=True, exist_ok=True)
        for artifact in phase.artifacts:
            (phase_dir / artifact["name"]).write_text(artifact["content"], encoding="utf-8")
            written += 1
    (out_dir / "journey.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return written


def _print_summary(result: JourneyResult) -> None:
    proj = result.project
    print(f"\nAPEX reference journey — {proj['name']} ({proj['slug']})")
    print("=" * 72)
    print(f"{'Phase':<14}{'Persona':<11}{'Authority':<11}{'Action':<9}{'Conf':<6}Outcome")
    print("-" * 72)
    for p in result.phases:
        print(
            f"{p.label:<14}{p.persona:<11}{p.authority:<11}{p.action:<9}"
            f"{p.confidence:<6.2f}{p.outcome}"
        )
    s = result.stats
    print("-" * 72)
    print(
        f"{s['phase_count']} phases · {s['artifact_count']} artifacts · "
        f"{s['auto_enforced_count']} auto-enforced · {s['human_review_count']} to human review · "
        f"gate bypasses: {s['confidence_gate_bypass_total']}"
    )


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    out_dir = Path(argv[0]).resolve() if argv else _DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    result = run_reference_journey(StubLLMProvider())
    written = _write_artifacts(result, out_dir)
    _print_summary(result)
    print(f"\nWrote {written} artifacts + journey.json under {out_dir}")

    if result.stats["confidence_gate_bypass_total"] != 0:
        print("ERROR: confidence_gate_bypass_total must be 0", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
