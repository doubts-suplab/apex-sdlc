# Customer Refunds — Onboarding Guide

1. `docker compose up` (Postgres + service).
2. Run migrations; seed a delivered order.
3. `POST /api/v1/refunds` with an eligible `order_id`.
4. Observe the outbox draining to the ledger and the audit entry written.
