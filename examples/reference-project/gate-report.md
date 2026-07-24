# Phase Gate Report — Customer Refunds Service

Generated offline by `python -m app.demo.gate_report`. The gate engine makes the spec-driven spine enforceable: a phase cannot advance until its gate passes.

## No approvals — the spine blocks at **requirements**

| Phase | Gate | Reason |
|---|---|---|
| requirements | pending | spec awaiting human approval |
| architecture | pending | spec awaiting human approval |
| development | passed | all gate criteria satisfied |
| testing | pending | spec awaiting human approval |
| cicd | passed | all gate criteria satisfied |
| docs | pending | spec awaiting human approval |
| governance | pending | spec awaiting human approval |

Development and CI/CD pass automatically (their decisions auto-enforced); the human-review specs (SUGGEST phases + the governance ALERT) are **pending** until a human approves.

## Every human-review spec approved — spine clears (all_passed = True)

| Phase | Gate | Reason |
|---|---|---|
| requirements | passed | all gate criteria satisfied |
| architecture | passed | all gate criteria satisfied |
| development | passed | all gate criteria satisfied |
| testing | passed | all gate criteria satisfied |
| cicd | passed | all gate criteria satisfied |
| docs | passed | all gate criteria satisfied |
| governance | passed | all gate criteria satisfied |
