# Prompt: ADR & Component Design (Architect)
# APEX Prompt Library · Category: Architect · Tool: Claude Code CLI + Claude.ai Desktop
# Maps to: Architecture phase · Agent: ArchitectureAgent (harness authority: SUGGEST → always human sign-off)

---

## Architecture Decision Record (ADR) Draft

```
You are a Solution Architect. Draft an Architecture Decision Record for the decision below. A SUGGEST
authority agent never self-approves — this ADR is a proposal for human sign-off.

Format (MADR-style):
# ADR-[NNN] — [Decision title]
Status: Proposed
## Context
[Forces at play: requirements, constraints, NFRs, bounded-context boundaries]
## Decision
[The choice, stated in the active voice]
## Consequences
[Positive (+) and negative (−) — be honest about the trade-offs]
## Alternatives considered
[2–3 options with why they were rejected]

Respect the golden rules: no cross-context DB joins, ports-and-adapters, explicit column lists,
parameterised queries, no hardcoded secrets.

Decision to record:
[DESCRIBE THE PROBLEM AND CANDIDATE APPROACHES]
```

---

## Component / C4 Diagram (Mermaid)

```
Produce a Mermaid diagram for the component below. Use `graph LR` for a component view or `C4Context`
for a context view. Show trust boundaries, synchronous vs asynchronous edges, and any anti-corruption
layer between bounded contexts. Do not invent components not in the description.

System description:
[DESCRIBE SERVICES, DATA STORES, EXTERNAL SYSTEMS, AND THEIR INTERACTIONS]
```

---

## Non-Functional Requirements Review

```
Review this design against non-functional requirements and flag gaps. For each NFR category, state the
current design position and any risk:
- Availability / SLO target and failure modes
- Scalability (statelessness, data partitioning, hot paths)
- Consistency model (and where eventual consistency surfaces to the user)
- Security (authN/authZ, PII handling, secrets, audit)
- Observability (logs, metrics, traces, correlation IDs)
- Cost (per-request and steady-state)

End with the top 3 NFR risks and a recommended mitigation for each.

Design:
[PASTE DESIGN / ADR / DIAGRAM]
```
