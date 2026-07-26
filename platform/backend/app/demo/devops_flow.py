"""DevOps-flow demo — an NL intent drives a governed, multi-tool DevOps pipeline, offline.

    python -m app.demo.devops_flow

Runs three intents through the harness-gated DevOps flow to show all three governance outcomes:
a fully-specified pipeline that **executes** five tools under authorization, an under-specified request
that is **held for human review** (no side effects), and an unrecognised request that **defers**. Writes
the execution log / plan artifacts to ``examples/devops-flow/`` and prints a summary.

No credentials required — the tool adapters are offline and deterministic.
"""

from __future__ import annotations

from pathlib import Path

from app.devops import run_devops_flow
from app.integrations.llm.stub_provider import StubLLMProvider

# app/demo/devops_flow.py → parents: demo, app, backend, platform, <repo root>
_REPO_ROOT = Path(__file__).resolve().parents[4]
_OUT = _REPO_ROOT / "examples" / "devops-flow"

_TARGETS = {
    "feature": "Refund retry fix",
    "project_id": "refund-service",
    "repo": "acme/refund-service",
    "base_branch": "main",
    "jira_project_key": "REF",
    "issue_type": "Story",
    "confluence_space": "REF",
    "slack_channel": "#refunds",
    "jenkins_job": "refund-service-ci",
}

_SCENARIOS = {
    "executed": (
        "ship the refund fix PR, run the build, file a story, publish the docs and tell the team",
        _TARGETS,
    ),
    # Recognised intent, but no concrete targets → held for human review, not executed.
    "held-for-review": ("open a PR and notify the team", {"feature": "Refund retry fix"}),
    # No DevOps intent at all → deferred.
    "deferred": ("what's the weather like", {}),
}


def main() -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    llm = StubLLMProvider()
    for label, (intent, context) in _SCENARIOS.items():
        result = run_devops_flow(llm=llm, intent=intent, context=context)
        scenario_dir = _OUT / label
        scenario_dir.mkdir(parents=True, exist_ok=True)
        for artifact in result.artifacts:
            (scenario_dir / artifact["name"]).write_text(artifact["content"], encoding="utf-8")
        d = result.decision
        print(
            f"{label:16s} → {d.action.name:8s} conf={d.confidence:.2f} "
            f"auto_enforced={d.auto_enforced} artifacts={len(result.artifacts)}"
        )
    print(f"\nWrote DevOps-flow examples under {_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
