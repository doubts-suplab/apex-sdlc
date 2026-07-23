# Prompt: Governance, Audit & Risk Review (CISO)
# APEX Prompt Library · Category: CISO · Tool: Claude.ai Desktop
# Maps to: Governance phase · Agent: ComplianceOfficerAgent (harness authority: BLOCK → auto-block only at ≥ 0.95)

---

## Audit-Log Review

```
You are a CISO reviewing the APEX audit log for a project. Every AI action is logged with actor, model,
phase, confidence, auto_enforced, and outcome. Summarise:
- Total agent runs, split by phase and by outcome (auto-enforced vs routed to human review)
- Any decision that auto-enforced at or above its authority threshold — confirm the threshold was met
- Any BLOCK/ALERT decisions and whether a human dispositioned them within SLA
- Any anomalies (e.g. confidence_gate_bypass_total > 0 — this must always be 0)

Flag anything that needs escalation to the AI Review Board.

Audit-log export:
[PASTE AUDIT LOG / JSON]
```

---

## PII-Event Triage

```
Triage these PII detection events from the PII guard. For each event state: field, pattern matched,
action taken (redacted / blocked), the agent run it came from, and whether any PII could have reached
the model. Group by severity. Recommend whether any event is a reportable incident.

Output a table sorted by severity, then a one-paragraph disposition.

PII events:
[PASTE PII EVENT LOG]
```

---

## ARB Risk Assessment

```
Prepare an Architecture Review Board risk assessment for the change below. Structure:
## Change summary
[What is changing and why]
## Risk register
| Risk | Likelihood | Impact | Mitigation | Residual risk | Owner |
## Policy compliance matrix
| Policy | Status (Pass/Fail/N-A) | Evidence |
## Recommendation
APPROVE / APPROVE-WITH-CONDITIONS / REJECT — with the specific conditions or reasons.

Anchor to the AI Usage Policy and the mainframe gate policy where relevant. Be explicit about any
control that is asserted but not evidenced.

Change / ADR / audit context:
[PASTE]
```
