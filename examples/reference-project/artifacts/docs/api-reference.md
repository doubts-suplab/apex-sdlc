# Customer Refunds — API Reference

## POST /api/v1/refunds
Initiate a refund for an eligible order.

**Request**
```json
{ "order_id": "ord_123", "refund_request_id": "rrq_abc" }
```

**Responses**
- `202 Accepted` — refund initiated (asynchronous ledger posting).
- `409 Conflict` — `already_refunded`.
- `422 Unprocessable` — `window_expired`.

All responses use RFC 7807 Problem Details on error.
