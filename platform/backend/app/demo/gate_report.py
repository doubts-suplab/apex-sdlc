"""Gate-report demo — evaluate the spec-driven spine's phase gates, offline.

    python -m app.demo.gate_report

Runs the reference journey, then evaluates every phase gate twice: with no approvals (the spine blocks at
the first human-review phase) and with every human-review spec approved (the spine clears). Prints both and
writes ``examples/reference-project/gate-report.md``. No DB / network / API keys.
"""

from __future__ import annotations

from pathlib import Path

from app.agents.orchestrator import run_reference_journey
from app.gates.engine import evaluate_journey
from app.integrations.llm.stub_provider import StubLLMProvider

_REPO_ROOT = Path(__file__).resolve().parents[4]
_OUT = _REPO_ROOT / "examples" / "reference-project" / "gate-report.md"


def _rows(gates: list[dict]) -> str:
    return "\n".join(f"| {g['phase']} | {g['status']} | {g['reason']} |" for g in gates)


def main(argv: list[str] | None = None) -> int:
    journey = run_reference_journey(StubLLMProvider())

    no_appr = evaluate_journey(journey, set())
    # Approve every phase that did not auto-enforce (i.e. every human-review spec).
    human_review = {p.phase for p in journey.phases if not p.auto_enforced}
    all_appr = evaluate_journey(journey, human_review)

    print(f"\nAPEX phase gates — {journey.project['name']}")
    print("=" * 64)
    print("No approvals:")
    for g in no_appr["gates"]:
        print(f"  {g['phase']:<13} {g['status']}")
    print(f"  → spine blocks at: {no_appr['blocking_phase']}")
    print("\nAll human-review specs approved:")
    for g in all_appr["gates"]:
        print(f"  {g['phase']:<13} {g['status']}")
    print(f"  → all passed: {all_appr['all_passed']}")

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(
        f"# Phase Gate Report — {journey.project['name']}\n\n"
        f"Generated offline by `python -m app.demo.gate_report`. The gate engine makes the spec-driven "
        f"spine enforceable: a phase cannot advance until its gate passes.\n\n"
        f"## No approvals — the spine blocks at **{no_appr['blocking_phase']}**\n\n"
        f"| Phase | Gate | Reason |\n|---|---|---|\n{_rows(no_appr['gates'])}\n\n"
        f"Development and CI/CD pass automatically (their decisions auto-enforced); the human-review specs "
        f"(SUGGEST phases + the governance ALERT) are **pending** until a human approves.\n\n"
        f"## Every human-review spec approved — spine clears (all_passed = {all_appr['all_passed']})\n\n"
        f"| Phase | Gate | Reason |\n|---|---|---|\n{_rows(all_appr['gates'])}\n",
        encoding="utf-8",
    )
    print(f"\nWrote {_OUT}")
    return 0 if journey.stats["confidence_gate_bypass_total"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
