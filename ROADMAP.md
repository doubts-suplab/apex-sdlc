# APEX SDLC Platform — Roadmap

## Vision

APEX is an enterprise AI-powered SDLC operating system that embeds autonomous AI agents at every phase of the software delivery lifecycle — from requirements through governance — giving engineering organisations a single control plane for project health, artifact generation, compliance enforcement, and team coordination across all products.

Unlike traditional dashboards that merely report on work, APEX actively participates in the SDLC: generating Gherkin user stories, writing ADRs, reviewing PRs, producing test plans, publishing Confluence pages, and enforcing phase gates — all with full audit trails, PII protection, and org-level oversight.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     APEX SDLC Platform                          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Next.js 14 Portal (App Router)              │   │
│  │   Persona views: Dev | BA | PM | QA | Lead | Architect   │   │
│  │                    | CISO                                 │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                            │  REST / SSE                        │
│  ┌─────────────────────────▼────────────────────────────────┐   │
│  │              FastAPI Backend  (/api/v1/)                  │   │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │   │
│  │   │ Services │  │  Agents  │  │     Middleware        │  │   │
│  │   │ layer    │  │ (Celery) │  │ PII Guard | Audit     │  │   │
│  │   └──────────┘  └──────────┘  └──────────────────────┘  │   │
│  └───┬──────┬──────────┬────────────┬────────┬─────────────┘   │
│      │      │          │            │        │                  │
│  ┌───▼──┐ ┌─▼────┐ ┌──▼───────┐ ┌──▼──┐ ┌──▼───────────────┐  │
│  │ PG   │ │Redis │ │Claude API│ │ S3  │ │  External APIs   │  │
│  │  16  │ │+Clry │ │opus-4-8  │ │Artf │ │ GitHub | Jira    │  │
│  │      │ │      │ │          │ │     │ │ Confluence       │  │
│  └──────┘ └──────┘ └──────────┘ └─────┘ └──────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Frontend framework | Next.js | 14 (App Router) | Server components reduce client JS; App Router enables nested layouts per persona |
| Frontend language | TypeScript | 5.x strict | Full type safety across API boundary |
| Frontend state | TanStack Query | v5 | Best-in-class async state, stale-while-revalidate, optimistic updates |
| Frontend styling | Tailwind CSS + shadcn/ui | latest | Design system consistency without a heavyweight UI library |
| Backend framework | FastAPI | 0.115+ | Async-native, auto OpenAPI, Pydantic v2 native integration |
| Backend language | Python | 3.12 | Latest LTS, best Anthropic SDK support |
| ORM | SQLAlchemy | 2.x async | Type-safe async queries, Alembic migration support |
| Database | PostgreSQL | 16 | JSONB for artifact metadata, full-text search, row-level security (future) |
| Task queue | Celery + Redis | 5.x / 7 | Long-running agent jobs run async; SSE streams progress back |
| AI SDK | Anthropic Python SDK | latest | Official SDK; streaming, tool use, and prompt caching support |
| AI model | claude-opus-4-8 | — | Best reasoning for artifact generation and code review |
| Cloud compute | AWS ECS Fargate | — | Serverless containers; no EC2 fleet management |
| Cloud database | RDS Aurora PostgreSQL | 16 | Managed, multi-AZ, auto-scaling storage |
| Cloud cache | ElastiCache Redis | — | Managed Redis for Celery broker + result backend |
| Object storage | S3 | — | Artifact versioned storage with lifecycle policies |
| IaC | AWS CDK | v2 | Python-native, type-checked infrastructure |
| CI/CD | GitHub Actions | — | Native GitHub integration; existing workflows retained |
| Local dev | Docker Compose | — | Deterministic local environment matching cloud topology |

---

## SDLC Agent Map

| Phase | Agent Role | Artifact Outputs | Destination |
|-------|-----------|-----------------|-------------|
| Requirements | Requirements Analyst | User stories (Gherkin), gap analysis, acceptance criteria, Jira epic/story structure | Jira epics + stories, artifact DB, Confluence |
| Architecture | Solution Architect | Architecture Decision Records (ADRs), project CLAUDE.md, component diagrams (Mermaid), tech debt register | Confluence ADR space, artifact DB, repo root |
| Development | PR Reviewer + Dev Coach | PR review comments (inline), test generation suggestions, code quality report, coverage delta analysis | GitHub PR comments, artifact DB |
| Testing | QA Analyst | Test plan document, test case suite, coverage gap analysis, QA checklist, regression pack | Confluence QA space, artifact DB, Jira test tasks |
| CI/CD | Release Engineer | Release notes (per tag), deployment checklist, rollback plan, environment diff | GitHub Releases, Confluence release page, artifact DB |
| Docs | Technical Writer | API reference (OpenAPI narrative), Confluence onboarding guide, README templates, changelog | Confluence, GitHub repo, artifact DB |
| Governance | Compliance Officer | Audit report, ARB prep deck (Markdown), risk register, PII event log, policy compliance matrix | Confluence governance space, artifact DB, CISO view |

---

## Build Phases

### Phase 1 — Foundation (Weeks 1–3)

Establish the running skeleton: API, DB, Docker environment, project registry.

**Deliverables:**
- `platform/backend/` FastAPI app with health endpoint and auto OpenAPI docs
- SQLAlchemy async engine + Alembic migrations for core entities: `organisations`, `projects`, `teams`, `members`, `phases`, `phase_gates`
- Project registry API (`/api/v1/projects`) — CRUD for organisations and projects
- `platform/docker-compose.yml` — postgres 16, redis 7, backend, frontend all wired
- `platform/frontend/` Next.js 14 scaffold with Tailwind + shadcn/ui, org home page (project grid), project detail page stub
- Structlog + correlation ID middleware
- GitHub Actions CI: lint (ruff, mypy), test (pytest-asyncio), build Docker image
- Absorb existing files: `governance/pii-guard/` → `backend/app/middleware/pii_guard/`, `automation/jira-bridge/` → `backend/app/integrations/jira/`, `automation/confluence-writer/` → `backend/app/integrations/confluence/`
- Rename `portal/` → `portal-prototype/`, delete `portal-live/`

**Exit gate:** `docker compose up` runs cleanly; `/api/v1/projects` returns 200; frontend loads at localhost:3000.

---

### Phase 2 — Integrations (Weeks 4–6)

Live data from GitHub, Jira, and Confluence per registered project.

**Deliverables:**
- GitHub integration: repository metadata, open PRs, branch list, recent commits, webhook receiver
- Jira integration: project board, epics, stories, sprint status per APEX project
- Confluence integration: space listing, page list, page create/update
- Per-project integration config stored in DB (`project_integrations` table)
- Frontend: project detail page shows live GitHub + Jira metrics (TanStack Query polling)
- Persona switcher (Developer / BA / PM / QA / Lead / Architect / CISO) — persisted to localStorage, filters KPI cards
- Background data refresh job (Celery beat, replaces `portal-data-refresh.yml` portal approach)
- Integration credential storage via AWS Secrets Manager (cloud) / `.env` (local)

**Exit gate:** Project detail page shows live PR count, open Jira stories, Confluence pages.

---

### Phase 3 — Agentic Flows (Weeks 7–10)

First AI agents running end-to-end: Requirements Analyst and PR Reviewer.

**Deliverables:**
- Agent orchestrator: `AgentContext` + `AgentResult` dataclasses, Celery task wrapper, SSE progress stream endpoint (`/api/v1/agents/{run_id}/stream`)
- `agent_runs` + `agent_run_messages` tables with full message history
- Requirements Analyst agent: ingests Jira project context + user-provided brief → produces Gherkin stories, writes back to Jira, stores artifact
- Development PR Reviewer agent: triggered by GitHub webhook on PR open/update → posts inline review comments to GitHub PR
- PII Guard middleware wired to all agent input/output (absorb from `governance/pii-guard/`)
- Audit log middleware: every agent run writes actor, model, token count, cost, before/after to `audit_log`
- Frontend: "Run Agent" button on phase panel → opens agent progress drawer with SSE streaming output
- Prompt library integration: load per-persona prompts from `prompts/` directory

**Exit gate:** Trigger Requirements agent from UI → Gherkin stories appear in Jira + artifact gallery.

---

### Phase 4 — Artifact Management (Weeks 11–13)

Versioned artifact storage, Confluence publishing, per-phase gallery.

**Deliverables:**
- `artifacts` + `artifact_versions` tables — content hash, S3 key, version lineage
- S3 client wrapper: upload artifact, generate pre-signed URL, lifecycle tagging
- Artifact publish flow: artifact → Confluence page (create or update with version comment)
- Per-phase artifact gallery in frontend: list artifacts, diff versions side-by-side, download, publish to Confluence button
- Remaining 5 agents: Architecture, Testing, CI/CD, Docs, Governance
- Agent output rendered in-app (Markdown → HTML, Mermaid diagrams via mermaid.js)
- CLAUDE.md template library served from `claude-templates/` — Architecture agent writes CLAUDE.md to project repo via GitHub API

**Exit gate:** All 7 phase agents run successfully; artifacts stored in S3; Confluence pages created.

---

### Phase 5 — Gates & Governance (Weeks 14–16)

Phase transition gates, ARB workflow, mainframe gate policy enforcement.

**Deliverables:**
- Phase gate engine: configurable criteria per gate (required artifacts, min test coverage, approved reviewers, policy checks)
- Gate evaluation API: `POST /api/v1/projects/{id}/phases/{phase}/gate/evaluate` → pass/fail + reason
- `policy_violations` + `pii_events` tables fully populated by middleware
- ARB workflow: Governance agent generates ARB prep document → ARB approver reviews in APEX → approval recorded in audit_log
- Mainframe gate policy enforced: block deployment artifact generation if mainframe change detected without signed-off gate doc
- CISO persona view: PII event log, policy violation heatmap, audit log export (CSV)
- Org-level governance dashboard: cross-project gate status, open violations, agent cost summary
- AWS CDK stack: ECS Fargate (backend + frontend), RDS Aurora, ElastiCache, S3, CloudWatch dashboards, Secrets Manager
- Load testing (Locust): agent endpoints under concurrent load

**Exit gate:** Phase gate blocks a deployment without required artifacts; ARB workflow completes end-to-end; CDK stack deploys to staging.

---

## File Inventory

| File / Directory | Current Status | Action |
|-----------------|---------------|--------|
| `automation/jira-bridge/handler.py` | Lambda webhook handler | Absorb into `platform/backend/app/integrations/jira/` |
| `automation/confluence-writer/writer.py` | Confluence REST client | Absorb into `platform/backend/app/integrations/confluence/` |
| `governance/pii-guard/guard.py` | PII detection middleware | Absorb into `platform/backend/app/middleware/pii_guard/` |
| `governance/pii-guard/patterns.py` | PII regex patterns | Absorb alongside guard.py |
| `governance/policies/` | AI usage + mainframe gate policies | Enforced by platform gate engine; retain as policy source files |
| `claude-templates/` | CLAUDE.md templates per project type | Used by Architecture agent as template library; stay in repo root |
| `prompts/` | Prompt library per persona | Loaded by agent orchestrator at runtime; stay in repo root |
| `.github/workflows/ai-pr-review.yml` | CI PR review workflow | Stay as-is (Phase 3 agent eventually replaces, but keep workflow) |
| `.github/workflows/ai-release-notes.yml` | CI release notes workflow | Stay as-is (Phase 4 CI/CD agent eventually replaces) |
| `.github/workflows/portal-data-refresh.yml` | Portal data refresh cron | Evolve to trigger backend Celery beat job; deprecate direct script call |
| `portal/` | Legacy portal prototype | Rename to `portal-prototype/` (Phase 1) |
| `portal-live/` | Superseded live portal | Delete (superseded by `platform/frontend/`) |
| `scripts/fetch_portal_data.py` | Data fetch script | Logic moves to `platform/backend/app/services/` |
| `platform/` | New — created in this roadmap | Primary codebase going forward |
| `platform/backend/` | New | FastAPI application root |
| `platform/frontend/` | New | Next.js 14 application root |
| `platform/docker-compose.yml` | New | Local dev environment |
| `platform/project-manifest.yaml` | New | eeik-bootstrap manifest |
| `platform/CLAUDE.md` | New | Master CLAUDE.md for AI agents |
| `platform/backend/CLAUDE.md` | New | Backend-specific agent instructions |
| `platform/frontend/CLAUDE.md` | New | Frontend-specific agent instructions |

---

## Data Model Overview

| Entity | Description |
|--------|-------------|
| `organisations` | Top-level tenant; an org owns multiple projects and has a billing/governance context |
| `projects` | A software project registered in APEX; belongs to an org; has its own GitHub repo, Jira project, Confluence space |
| `teams` | A team within an org; members of a team inherit access to projects the team is assigned to |
| `members` | A user with a persona role (Developer / BA / PM / QA / Lead / Architect / CISO) within a project |
| `phases` | An SDLC phase instance for a project (Requirements, Architecture, Development, Testing, CI/CD, Docs, Governance) |
| `phase_gates` | Gate configuration for a phase transition: required artifacts, approvers, policy checks, current pass/fail state |
| `artifacts` | A generated document or output produced by an agent for a project phase (user stories, ADR, test plan, etc.) |
| `artifact_versions` | Immutable version of an artifact: content hash, S3 key, Confluence page ID, created timestamp |
| `agent_runs` | A single execution of a phase agent: model used, total tokens, cost USD, duration, status, actor |
| `agent_run_messages` | Individual message turns within an agent run (system, user, assistant) with token counts |
| `audit_log` | Append-only log of every AI action: actor, model, phase, artifact, before state, after state, timestamp |
| `pii_events` | Record of every PII detection event: field, pattern matched, action taken (redacted/blocked), agent run reference |
| `policy_violations` | Policy check failures: which policy, which project/phase, severity, remediation status |
