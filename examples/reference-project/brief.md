# Reference Project Brief — Customer Refunds Service

**Requested by:** Program Manager · **For:** the Payments squad

> Let customers request a refund on a delivered order without contacting support. Refunds must be
> eligibility-checked server-side, auditable, idempotent, and must never leak customer PII.

**Stack:** Spring Boot 3.x / Java 21 / PostgreSQL
**Target version:** v1.0.0

This one-paragraph brief is the single input to the APEX reference journey. Everything in
[`artifacts/`](artifacts/) is generated from it by the seven phase agents, each governed by the
[agent-harness](https://github.com/doubts-suplab/agent-harness). Regenerate the whole journey with:

```bash
cd platform/backend && LLM_PROVIDER=stub python -m app.demo.reference_journey
```
