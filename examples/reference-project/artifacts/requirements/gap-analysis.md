# Customer Refunds — Requirements Gap Analysis

Brief analysed:

> Let customers request a refund on a delivered order without contacting support. Refunds must be eligibility-checked server-side, auditable, idempotent, and must never leak customer PII.

| Area | Covered by brief | Gap flagged for the BA |
|---|---|---|
| Happy-path refund | Yes | — |
| Refund window rules | Partially | Exact window length not specified |
| Partial refunds | No | Is a partial refund in scope for v1? |
| Idempotency | No | Define behaviour on duplicate refund requests |
| Downstream ledger | No | Which system of record posts the credit? |

**Recommendation:** resolve the four gaps above before the Architecture phase.
