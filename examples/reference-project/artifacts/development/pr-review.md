# Customer Refunds — PR Review

> Advisory review by the PR Reviewer agent (harness authority: ALERT). Auto-enforced advisory posting when confident; a human still merges.

- **[MAJOR]** RefundService.initiate() builds SQL by string concatenation — use a parameterised query.
- **[MAJOR]** Customer email is logged at INFO in RefundController — PII must not be logged.
- **[MAJOR]** No test covers the 'already_refunded' rejection path.
