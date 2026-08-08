---
name: Feature request
about: Propose a capability or improvement for APEX
title: "feat: "
labels: enhancement
assignees: ''
---

## Problem / motivation

What can't you do today, or what's harder than it should be? Who is it for (which persona — Developer, BA,
PM, QA, Lead, Architect, CISO)?

## Proposed solution

What you'd like APEX to do. If it maps to an existing item on the roadmap, link it:
[ROADMAP.md](../../ROADMAP.md) · [docs/progress.md](../../docs/progress.md).

## Scope and feasibility

Help triage by tagging your best guess:

- **Target phase:** Phase 0 (onboarding) / 2 (integrations) / 3 (agentic flows) / 4 (artifacts) /
  5 (gates & governance)
- **Feasibility:**
  - [ ] `offline` — buildable and verifiable with no credentials or infra
  - [ ] `credential-gated` — needs GitHub/Jira/Confluence/Anthropic credentials
  - [ ] `infra-gated` — needs Postgres/Redis/S3/AWS

## Governance considerations

APEX is governed by design. If your request involves an AI action, note:

- Which **authority level** it should hold (OBSERVE / SUGGEST / ALERT / RATE_LIMIT / BLOCK), and whether it
  should ever auto-enforce (remember: SUGGEST phases never auto-enforce — gate rule G-5).
- Whether it produces a new artifact, a write-back side effect, or a policy/audit implication.

## Alternatives considered

Anything you ruled out, and why.
