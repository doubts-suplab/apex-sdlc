# APEX Personas & Phase Ownership

> **Single source of truth.** This table mirrors `platform/backend/app/agents/catalog.py`
> (the executable catalog the orchestrator, the journey API, and the frontend all derive from) and
> `platform/frontend/src/types/project.ts` (`PersonaSchema` / `PhaseTypeSchema`). When any of those
> change, update this file in the same commit.

APEX serves **seven personas** across **seven SDLC phases**. Every phase is run by an AI agent on the
generic [agent-harness](https://github.com/doubts-suplab/agent-harness) runtime. The agent *proposes* a
decision; the harness *governs* whether it may auto-enforce (confidence gate), which tools it may touch
(default-deny registry), and records every action to an append-only, PII-redacted audit log. An agent
never sets its own enforcement.

## The seven personas

| Persona | Owns (primary phase) | Contributes to / consumes | What APEX gives them |
|---|---|---|---|
| **Business Analyst (`ba`)** | Requirements | Architecture (hand-off) | Gherkin stories + gap analysis drafted from a brief, for approval |
| **Architect (`architect`)** | Architecture | Requirements, Development, Governance | ADR + component diagram + tech-debt register, for sign-off |
| **Developer (`developer`)** | Development, Docs | Architecture, Testing | Advisory PR review + quality report; API/onboarding docs |
| **QA Engineer (`qa`)** | Testing | Development | Test plan + BDD cases + coverage-gap analysis, for approval |
| **Tech Lead (`lead`)** | CI/CD | Development, Governance | Release notes + deployment checklist + rollback plan |
| **Program Manager (`pm`)** | — (cross-cutting) | Requirements, SDLC timeline, metrics | Portfolio view: phase status, gate health, agent cost |
| **CISO (`ciso`)** | Governance | All phases (oversight) | Audit report + risk register; PII events; ARB prep |

## Phase → persona → agent → authority → artifacts

The **authority level** is the agent's static ceiling on the harness. Crucially, the harness gate rule
G-5 means **OBSERVE/SUGGEST-authority agents can never auto-enforce** — so the four SUGGEST phases below
*always* route to a human. This is APEX's founding principle — *"AI generates drafts; humans approve"* —
expressed directly through the harness authority ladder, not re-implemented in app code.

| Phase | Persona | Agent (`class`) | Authority | Typical outcome | Artifacts | eeik agent |
|---|---|---|---|---|---|---|
| Requirements | BA | `RequirementsAgent` | SUGGEST | → human review | `user-stories.md`, `gap-analysis.md` | `business-analyst` |
| Architecture | Architect | `ArchitectureAgent` | SUGGEST | → human review | ADR, `component-diagram.mmd`, `tech-debt.md` | `architect` |
| Development | Developer | `PRReviewerAgent` | ALERT | auto-enforced advisory (when confident) | `pr-review.md`, `quality-report.md` | `code-reviewer` |
| Testing | QA | `QAAnalystAgent` | SUGGEST | → human review | `test-plan.md`, `test-cases.md`, `coverage-gaps.md` | `tester` |
| CI/CD | Tech Lead | `ReleaseEngineerAgent` | RATE_LIMIT | auto-enforced release (when green) | `release-notes.md`, `deployment-checklist.md`, `rollback-plan.md` | `ci-engineer` |
| Docs | Developer | `TechWriterAgent` | SUGGEST | → human review | `api-reference.md`, `onboarding-guide.md` | `technical-writer` |
| Governance | CISO | `ComplianceOfficerAgent` | BLOCK | auto-block only at ≥ 0.95; else human review | `governance-report.md`, `risk-register.md` | `security-auditor` |

## Authority ladder & the confidence gate

```
OBSERVE  <  SUGGEST  <  ALERT  <  RATE_LIMIT  <  BLOCK
                │          │           │            │
   never auto-enforce      └──── auto-enforce only when confidence ≥ threshold ────┘
   (G-5: humans approve)        ALERT 0.80   RATE_LIMIT 0.85   BLOCK 0.95
```

- **Confidence gate** — centralized in the harness core, runs on *every* invocation, cannot be disabled.
  It is the *only* place `auto_enforced` is set.
- **Human-in-the-loop** — any non-enforcing decision (all SUGGEST phases, low-confidence ALERT/BLOCK,
  every DEFER) is routed to a human review queue with an SLA.
- **Safe by default** — any agent/LLM/tool failure resolves to a safe, non-enforcing decision with
  lowered confidence. `confidence_gate_bypass_total` must always be `0`.

See the [reference journey](../examples/reference-project/README.md) for a worked example of one project
walking all seven phases, and [`ROADMAP.md`](../ROADMAP.md) for the platform build plan.
