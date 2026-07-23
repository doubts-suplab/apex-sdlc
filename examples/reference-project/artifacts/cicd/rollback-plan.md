# Rollback Plan (v1.0.0)

- Repoint the router to the previous colour (no data loss; migration is additive).
- Refunds are idempotent, so in-flight retries are safe after rollback.
- If the ledger already posted, no compensating action is required.
