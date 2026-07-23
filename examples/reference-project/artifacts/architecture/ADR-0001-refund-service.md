# ADR-0001 — Customer Refunds bounded context

Status: **Proposed** (awaiting architect sign-off — harness routed to human review)

## Context
Customer Refunds must evaluate refund eligibility server-side, initiate a credit, and remain auditable. It integrates with the orders read-model and a downstream ledger.

## Decision
- Implement as a standalone Spring Boot service (Spring Boot 3.x / Java 21 / PostgreSQL) with a hexagonal layering (domain / application / infrastructure / web).
- Own a `refunds` bounded context; read order state via an anti-corruption port, never a cross-context DB join.
- Enforce idempotency with a client-supplied `refund_request_id` unique key.
- Post the credit to the ledger through an outbox + async publisher (no dual-write).

## Consequences
- (+) Clear ownership, auditable decisions, no distributed transaction.
- (−) Eventual consistency between refund initiation and ledger posting; surfaced to the customer as "in progress".
