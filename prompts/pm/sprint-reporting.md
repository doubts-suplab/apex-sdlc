# Prompt: Sprint Reporting (Program Manager)
# APEX Prompt Library · Category: PM · Tool: Claude.ai Desktop + Copilot M365

---

## Jira Export → Executive Status Update

```
You are a Program Manager. Convert this Jira sprint export into a concise executive status update.

Format:
**[Project Name] — Sprint [N] Status Update**
**Date:** [date] | **Sprint:** [start] – [end]

**Delivered this sprint**
[3–5 bullet points — business outcomes, not ticket titles]

**In progress / carrying forward**
[2–3 bullet points with brief reason for carry-forward]

**Risks & blockers**
[List with owner and mitigation — or "None this sprint"]

**Next sprint priorities**
[Top 3 items planned]

**Key metrics**
- Velocity: [X] SP delivered vs [Y] SP committed ([Z]%)
- Bugs found/fixed: [N]/[M]
- Carry-forward: [N] stories

Tone: plain English, confident, no jargon, suitable for CTO/Director audience.

Jira export:
[PASTE SPRINT DATA / CSV / JSON]
```

---

## Sprint Retrospective Synthesis

```
Synthesise these retrospective sticky notes / Miro board export into a structured retro summary.

Format:
## Sprint [N] Retrospective Summary

### What went well
[Theme → specific examples]

### What didn't go well
[Theme → specific examples]

### Action items
| Action | Owner | Due | Priority |
|--------|-------|-----|---------|
| ...    | ...   | ... | High/Med/Low |

### Patterns across last 3 sprints
[Identify any recurring themes that need escalation]

### Team health signal
[Green / Amber / Red] — reason in one sentence

Retro notes:
[PASTE]
```

---

## Risk Register Update

```
Update this risk register based on the latest sprint outcomes.

For each risk:
- Has the likelihood changed? (increase / decrease / same)
- Has the impact changed?
- Is the mitigation still valid or needs updating?
- Has any risk become an issue (materialised)?

Add new risks identified this sprint.
Remove risks that are now closed.

Output as a markdown table:
| ID | Risk | Likelihood | Impact | Mitigation | Owner | Status |

Current risk register:
[PASTE]

Sprint outcomes and blockers:
[PASTE]
```

---

## Release Go/No-Go Report

```
Generate a release go/no-go report for [Release Name / Version].

Assess each gate:
- [ ] Feature completeness: [X/Y stories done]
- [ ] Test coverage: [%] (gate: 80%)
- [ ] Open P1/P2 bugs: [count] (gate: 0 P1, <3 P2)
- [ ] Performance test results: pass/fail
- [ ] Security scan: pass/fail
- [ ] UAT sign-off: obtained / pending
- [ ] Deployment runbook: reviewed / pending
- [ ] Rollback plan: documented / pending
- [ ] Stakeholder comms: sent / pending

Decision: GO / NO-GO / CONDITIONAL GO (with conditions listed)

Data:
[PASTE — Jira metrics, test results, UAT status]
```
