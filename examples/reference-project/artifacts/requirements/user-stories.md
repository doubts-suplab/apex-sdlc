# Customer Refunds — User Stories

> Drafted by the Requirements Analyst agent from the project brief. Status: **[AI-Draft]** — awaiting BA approval (harness routed to human review).

```gherkin
Feature: Customer Refunds
  As a customer
  I want to request a refund for an eligible order
  So that I am reimbursed without contacting support

  Scenario: Eligible order is refunded
    Given an order that was delivered within the refund window
    And the order has not already been refunded
    When the customer requests a refund
    Then a refund is initiated for the order total
    And the customer is notified the refund is in progress

  Scenario: Refund window has expired
    Given an order delivered outside the refund window
    When the customer requests a refund
    Then the request is rejected with reason "window_expired"

  Scenario: Order already refunded
    Given an order that has already been fully refunded
    When the customer requests a refund
    Then the request is rejected with reason "already_refunded"
```

## Acceptance criteria
- Refund eligibility is evaluated server-side; the client never asserts eligibility.
- Every refund decision is auditable (who, when, amount, reason).
- Customer PII is never written to logs (governance-gated downstream).
