# Deployment Checklist

1. Run DB migration `V1__refunds.sql` (additive, no downtime).
2. Deploy service (blue/green); verify `/health` green.
3. Smoke test: eligible refund + rejection paths.
4. Confirm outbox publisher draining to the ledger.
