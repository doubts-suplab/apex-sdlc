# Customer Refunds — Release Notes (v1.0.0)

## Features
- Customer-initiated refunds for eligible orders.

## Fixes
- Reject refunds outside the window and on already-refunded orders.

## Notes
- Idempotent via `refund_request_id`. Ledger posting is asynchronous.
