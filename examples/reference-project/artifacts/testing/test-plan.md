# Customer Refunds — Test Plan

Status: **[AI-Draft]** — awaiting QA sign-off (harness routed to human review).

| Aspect | Approach |
|---|---|
| Scope | Refund eligibility, initiation, idempotency, rejection paths |
| Levels | Unit (domain), slice (web), integration (Testcontainers Postgres) |
| Entry | Stories approved, ADR signed off |
| Exit | 80% line / 70% branch, all rejection paths covered |
| Environments | Ephemeral Testcontainers; no production data |
