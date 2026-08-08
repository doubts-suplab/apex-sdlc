#!/usr/bin/env python3
"""One-command offline smoke test for APEX.

    cd platform/backend && python scripts/smoke_test.py     # or: make smoke (from repo root)

Runs the offline fixture-regenerating demos, asserts the committed ``examples/`` tree is still
**byte-identical** afterwards (proof the code and the committed fixtures have not drifted), then runs a
governance-focused test subset. Everything is offline — the stub LLM provider, no DB/network/API keys.

Exit code 0 = every stage passed. Non-zero = the first failing stage (with its output).

Assumes a clean ``examples/`` checkout: the byte-identical check compares the working tree against
git HEAD, so uncommitted fixture edits made *before* running will be reported as drift.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# platform/backend/scripts/smoke_test.py → parents: scripts, backend, platform, <repo root>
_BACKEND = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND.parents[1]

# Offline demos that regenerate committed fixtures under examples/. eeik_engine_demo is intentionally
# excluded: it depends on the optional eeik SDK/MCP and skips when eeik is absent, so it is not part of
# the deterministic offline baseline.
_DEMOS = [
    "app.demo.reference_journey",
    "app.demo.gate_report",
    "app.demo.generate_repo",
    "app.demo.devops_flow",
    "app.demo.onboard_project",
]

# A fast, governance-focused test subset — the guarantees APEX makes (authority ladder, gates, journey).
_TESTS = ["tests/agents", "tests/gates"]

_GREEN = "\033[32m"
_RED = "\033[31m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _run(cmd: list[str], *, env_stub: bool = False) -> subprocess.CompletedProcess[str]:
    env = None
    if env_stub:
        import os

        env = {**os.environ, "LLM_PROVIDER": "stub"}
    return subprocess.run(
        cmd,
        cwd=_BACKEND,
        env=env,
        capture_output=True,
        text=True,
    )


def _fail(stage: str, detail: str) -> int:
    print(f"\n{_RED}{_BOLD}✗ {stage} failed{_RESET}\n")
    if detail.strip():
        print(detail.rstrip())
    print(f"\n{_RED}{_BOLD}SMOKE TEST FAILED{_RESET}")
    return 1


def main() -> int:
    print(f"{_BOLD}APEX offline smoke test{_RESET}  {_DIM}(python {sys.version.split()[0]}){_RESET}\n")

    # Stage 1 — regenerate every offline fixture.
    print(f"{_BOLD}1. Regenerating offline fixtures{_RESET}")
    for module in _DEMOS:
        result = _run([sys.executable, "-m", module], env_stub=True)
        if result.returncode != 0:
            return _fail(f"demo {module}", result.stdout + result.stderr)
        print(f"   {_GREEN}✓{_RESET} {module}")

    # Stage 2 — the fixtures must be byte-identical to what is committed.
    print(f"\n{_BOLD}2. Asserting examples/ is byte-identical{_RESET}")
    status = _run(["git", "-C", str(_REPO_ROOT), "status", "--porcelain", "--", "examples"])
    if status.returncode != 0:
        return _fail("git status", status.stdout + status.stderr)
    if status.stdout.strip():
        diff = _run(["git", "-C", str(_REPO_ROOT), "diff", "--stat", "--", "examples"])
        detail = (
            "Regenerating the demos changed the committed fixtures:\n\n"
            + status.stdout
            + "\n"
            + diff.stdout
            + "\nIf this change is intentional, commit the new examples/. "
            "Otherwise the code has drifted from the fixtures."
        )
        return _fail("byte-identical examples/", detail)
    print(f"   {_GREEN}✓{_RESET} examples/ unchanged")

    # Stage 3 — a governance-focused test subset.
    print(f"\n{_BOLD}3. Running governance test subset{_RESET}  {_DIM}({', '.join(_TESTS)}){_RESET}")
    # `-o addopts=` clears the coverage flags from pyproject so the subset runs fast and standalone.
    tests = _run([sys.executable, "-m", "pytest", "-o", "addopts=", "-q", *_TESTS])
    if tests.returncode != 0:
        return _fail("pytest", tests.stdout + tests.stderr)
    # Surface pytest's summary line.
    summary = [ln for ln in tests.stdout.splitlines() if "passed" in ln or "failed" in ln]
    print(f"   {_GREEN}✓{_RESET} {summary[-1].strip() if summary else 'tests passed'}")

    print(f"\n{_GREEN}{_BOLD}SMOKE TEST PASSED{_RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
