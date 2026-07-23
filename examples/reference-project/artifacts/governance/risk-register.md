# Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| PII in logs (flagged in PR review) | Medium | High | Redact in web layer; PII guard |
| SQL injection (flagged in PR review) | Low | Critical | Parameterised queries only |
| Ledger posting lag | Medium | Medium | Outbox + retry; surface "in progress" |
