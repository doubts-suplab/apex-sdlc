# Customer Refunds — Test Cases (mapped to stories)

| ID | Story | Given → When → Then | Type |
|---|---|---|---|
| TC-1 | Eligible refund | delivered in window → request → refund initiated | integration |
| TC-2 | Window expired | delivered out of window → request → rejected(window_expired) | unit |
| TC-3 | Already refunded | refunded order → request → rejected(already_refunded) | unit |
| TC-4 | Idempotency | same refund_request_id twice → one refund | integration |
