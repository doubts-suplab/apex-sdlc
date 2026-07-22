# APEX SDLC Platform — Master CLAUDE.md

## Project Brief

APEX is an enterprise AI-powered SDLC operating platform. It is not a dashboard — it is a control plane that actively participates in the software delivery lifecycle across an entire organisation. It onboards multiple projects, provides persona-specific views (Developer, BA, PM, QA, Lead, Architect, CISO), runs AI agents at each SDLC phase to generate artifacts, enforces phase transition gates, and writes outputs to Jira, Confluence, and GitHub with a full audit trail for every AI action.

This is not a reporting dashboard. It is an active participant in the SDLC: it generates Gherkin stories, writes ADRs, reviews PRs, produces test plans, publishes Confluence pages, and enforces phase gates. Every AI action is logged with model, token count, cost, actor, and full before/after state.

Think of it as CA Agile Central (Rally) with Claude embedded at every SDLC phase.

---

## Architecture

```
Next.js 14 Portal (App Router)
        │
        │  REST + SSE
        ▼
FastAPI Backend  /api/v1/
        │
        ├── Services layer      (business logic, no HTTP coupling)
        ├── Agent orchestrator  (Celery tasks, Claude API calls)
        ├── Middleware          (PII guard, audit, auth, correlation ID)
        │
        ├── PostgreSQL 16       (primary data store, JSONB for artifact metadata)
        ├── Redis + Celery      (task queue broker + result backend)
        ├── S3                  (artifact versioned storage, lifecycle policies)
        └── External APIs
              ├── Anthropic API  (claude-opus-4-8 — all agent runs)
              ├── GitHub REST v3 (repo data, PR comments, file writes, webhooks)
              ├── Jira Agile v1  (epics, stories, sprint boards, issue creation)
              └── Confluence v2  (pages create/update, space management)
```

Long-running agent jobs run as Celery tasks (broker: Redis). The frontend streams progress via SSE (`GET /api/v1/agents/{run_id}/stream`).

---

## Tech Stack Per Layer

| Layer | Technology | Notes |
|-------|-----------|-------|
| Portal framework | Next.js 14 App Router | Server components by default; SSE for agent streaming |
| Portal language | TypeScript strict | No `any` types; Zod schemas mirror backend Pydantic models |
| Portal state | TanStack Query v5 | All API calls go through TanStack Query hooks |
| Portal styling | Tailwind CSS + shadcn/ui | shadcn/ui components only; no other component libraries |
| API framework | FastAPI 0.115+ | Async-native; auto OpenAPI at /docs |
| API language | Python 3.12 | Type-annotated throughout; no implicit `Any` |
| ORM | SQLAlchemy 2.x async | `AsyncSession` everywhere; `selectinload` for relationships |
| Migrations | Alembic | One migration per schema change; never edit existing migrations |
| Validation | Pydantic v2 | `model_validate()` not `.parse_obj()`; `model_config` not `class Config` |
| Logging | structlog | JSON output in prod; key-value in dev; correlation ID on every request |
| Task queue | Celery 5.x + Redis | Agent runs are Celery tasks; progress streamed via SSE |
| AI model | claude-opus-4-8 | Via Anthropic Python SDK; streaming enabled for agent progress |
| Cloud | AWS (ECS Fargate, RDS Aurora, ElastiCache, S3) | CDK v2 Python for IaC |

---

## Directory Structure

```
platform/
  backend/
    app/
      api/
        v1/
          projects.py         CRUD for organisations + projects
          phases.py           Phase status, gate evaluation
          artifacts.py        Artifact list, version history, download
          agents.py           Trigger agent run, stream progress (SSE)
          governance.py       Audit log, PII events, policy violations
          auth.py             JWT issue/refresh (Phase 5)
      agents/
        base.py               AgentContext, AgentResult dataclasses, BaseAgent ABC
        orchestrator.py       Celery task wrapper, SSE event emitter
        requirements.py       RequirementsAgent
        architecture.py       ArchitectureAgent
        development.py        PRReviewerAgent
        testing.py            QAAnalystAgent
        cicd.py               ReleaseEngineerAgent
        docs.py               TechWriterAgent
        governance.py         ComplianceOfficerAgent
      integrations/
        github/
          client.py           GitHub REST v3 wrapper (httpx AsyncClient)
          webhooks.py         Webhook signature verification + event dispatch
        jira/
          client.py           Jira Agile REST v1 wrapper (httpx AsyncClient)
          models.py           Jira entity dataclasses
        confluence/
          client.py           Confluence REST v2 wrapper (httpx AsyncClient)
        anthropic/
          client.py           Anthropic SDK wrapper, streaming helper
          prompt_loader.py    Loads prompts from /prompts/ directory
      middleware/
        pii_guard.py          PII detection on all agent I/O; writes pii_events
        audit.py              Logs every AI action to audit_log
        auth.py               JWT validation middleware (Phase 5)
        correlation.py        Injects X-Correlation-ID on every request
      models/
        organisation.py       Organisation ORM model
        project.py            Project + ProjectIntegration ORM models
        team.py               Team + Member ORM models
        phase.py              Phase + PhaseGate ORM models
        artifact.py           Artifact + ArtifactVersion ORM models
        agent_run.py          AgentRun + AgentRunMessage ORM models
        audit.py              AuditLog + PiiEvent + PolicyViolation ORM models
      schemas/
        project.py            ProjectCreate, ProjectRead, ProjectUpdate Pydantic schemas
        phase.py              PhaseRead, GateEvaluationResult schemas
        artifact.py           ArtifactRead, ArtifactVersionRead schemas
        agent.py              AgentRunCreate, AgentRunRead, AgentProgress schemas
        governance.py         AuditLogRead, PiiEventRead, PolicyViolationRead schemas
      services/
        project_service.py    Project + org business logic
        phase_service.py      Phase state machine, gate evaluation logic
        artifact_service.py   Artifact CRUD + S3 upload + versioning
        agent_service.py      Agent run lifecycle: create, update, complete
        integration_service.py  Per-project integration config CRUD
      db/
        session.py            AsyncSession factory, get_db FastAPI dependency
        base.py               DeclarativeBase, TimestampMixin
        migrations/           Alembic env.py and versions/
      core/
        config.py             Settings (pydantic-settings, reads .env)
        security.py           JWT helpers (Phase 5)
        logging.py            structlog configuration
    tests/
      conftest.py             pytest fixtures: async client, test DB session, factories
      api/                    API-level integration tests (one file per router)
      services/               Service layer unit tests
      agents/                 Agent unit tests (mocked Anthropic API responses)
      integrations/           Integration client tests (VCR cassettes)
    alembic.ini
    pyproject.toml
    Dockerfile
    .env.example

  frontend/
    src/
      app/
        (org)/
          page.tsx            Org home — project grid with health KPIs
        projects/
          [id]/
            page.tsx          Project detail — SDLC timeline, live metrics
            phase/
              [phase]/
                page.tsx      Phase detail — artifact list, Run Agent button
            generate/
              page.tsx        Artifact generator — select phase + prompt
        governance/
          page.tsx            Org governance — audit log, gates, violations
        layout.tsx            Root layout — nav, persona switcher
      components/
        ui/                   shadcn/ui component wrappers only
        layout/
          Navbar.tsx
          Sidebar.tsx
          PersonaSwitcher.tsx  Persona dropdown — persisted to localStorage
        projects/
          ProjectCard.tsx
          SDLCTimeline.tsx     Phase lane view with gate status indicators
        phases/
          PhasePanel.tsx
          ArtifactCard.tsx
          ArtifactDiff.tsx     Side-by-side version diff viewer
        agents/
          AgentRunDrawer.tsx   Slide-in panel for agent progress
          AgentProgress.tsx    SSE streaming output renderer
          AgentOutput.tsx      Markdown + Mermaid rendered artifact
      lib/
        api.ts                fetch/axios client — base URL from env
        queries/
          projects.ts         useProjects, useProject, useMutateProject
          phases.ts           usePhase, useGateStatus
          artifacts.ts        useArtifacts, useArtifactVersion
          agents.ts           useAgentRun, useAgentStream (SSE hook)
          governance.ts       useAuditLog, usePiiEvents, usePolicyViolations
      types/
        project.ts            TypeScript interfaces matching backend schemas
        phase.ts
        artifact.ts
        agent.ts
        governance.ts
    public/
    Dockerfile
    next.config.ts

  docker-compose.yml
  project-manifest.yaml
  CLAUDE.md               (this file)
  README.md
```

---

## Core Data Model

| Entity | Description |
|--------|-------------|
| `organisations` | Top-level tenant; owns projects, has billing + governance context |
| `projects` | A software project; has GitHub repo, Jira project key, Confluence space key, current SDLC phase |
| `teams` | A team within an org; assigned to one or more projects |
| `members` | User with a persona role (Developer/BA/PM/QA/Lead/Architect/CISO) in a project |
| `phases` | SDLC phase instance per project (Requirements → Architecture → Development → Testing → CI/CD → Docs → Governance) |
| `phase_gates` | Gate criteria for a phase transition: required artifacts, min coverage, approvers, policy checks, current pass/fail state |
| `artifacts` | AI-generated document for a project phase (user stories, ADR, test plan, release notes, etc.) |
| `artifact_versions` | Immutable artifact version: SHA-256 content hash, S3 key, Confluence page ID, created timestamp |
| `agent_runs` | One execution of a phase agent: model, total tokens, cost_usd, duration, status, actor user |
| `agent_run_messages` | Individual message turns within an agent run (system/user/assistant) with per-turn token counts |
| `audit_log` | Append-only record of every AI action: actor, model, phase, artifact before/after state, timestamp |
| `pii_events` | PII detection event: matched pattern, field name, action taken (redacted/blocked), agent run FK |
| `policy_violations` | Policy check failure: policy name, project/phase, severity, remediation status |

---

## eeik-Bootstrap Agent Map

Use the correct eeik agent for each task category. Do not use a general-purpose agent for specialised tasks.

| Task Category | eeik Agent | When to use |
|--------------|-----------|-------------|
| FastAPI routers, services, schemas | `python-developer` | Adding or modifying any backend Python code |
| DB schema design, Alembic migrations | `dba-advisor` | Any schema changes or query optimisation |
| SQLAlchemy ORM models | `python-developer` + `dba-advisor` | Complex relationships; always review with dba-advisor |
| AWS CDK stack, ECS, RDS | `aws-architect` | Infrastructure changes, any new AWS services |
| Anthropic API integration, agent design | `ai-engineer` | Agent implementations, prompt engineering, streaming |
| Multi-agent orchestration, Celery flows | `ai-engineer` + `python-developer` | Orchestrator patterns, task chaining |
| LangGraph-style flows (if adopted) | `langraph-engineer` | If agent orchestration moves to LangGraph |
| Next.js components, TanStack Query hooks | `react-developer` | All frontend implementation work |
| Security review, PII guard | `security-auditor` + `devsecops-engineer` | Middleware changes, auth implementation |
| API design, OpenAPI spec | `architect` | New resource design, breaking API changes |
| CI/CD pipeline changes | `ci-engineer` | GitHub Actions changes, CDK pipeline updates |
| Docker, docker-compose | `containerisation-helper` | Container configuration, Dockerfile changes |
| ADR creation | `architect` + `/adr` command | Architecture decisions requiring a record |
| Effort estimates | `estimator` + `/estimate` command | Sprint planning, feature sizing |

---

## SDLC Phase Agent Specifications

Phase agents run on the generic **agent-harness** runtime
([`doubts-suplab/agent-harness`](https://github.com/doubts-suplab/agent-harness)) — APEX does not
re-implement agent execution. Each agent extends `PhaseAgent` (`backend/app/agents/base.py`), which
satisfies the harness `Agent` protocol; the harness owns the confidence gate, tool registry, audit, human
review, and safe-failure defaults. An agent proposes a `Decision`; the harness decides whether it may
auto-enforce. See `backend/CLAUDE.md` → *Agent Implementation Pattern* and the harness protocol spec.

```python
class PhaseAgent(ABC):                       # app/agents/base.py — satisfies the harness Agent protocol
    name: str
    authority_level: AuthorityLevel          # static capability ceiling
    capabilities: frozenset[DecisionAction]  # actions it may emit
    def decide(self, ctx: AgentContext, tools: ToolInvoker) -> Decision: ...
```

### Agent Invocation Flow

1. Portal sends `POST /api/v1/projects/{id}/phases/{phase}/agents/run` with input payload
2. API validates inputs, runs PII guard, creates `agent_run` record (status=pending)
3. Celery task builds the harness (`build_apex_harness`) and calls `run_agent(harness, agent, ctx)`
4. The **harness** invokes the agent: scope check → tool-registry-enforced execution → **confidence gate**
   sets `auto_enforced` → routes low-confidence/DEFER decisions to human review → audit + observability
5. On completion: artifact saved → S3 upload → `artifact_versions` record created → `audit_log` entry written
6. Frontend reads SSE endpoint `GET /api/v1/agents/{run_id}/stream` for live progress

---

### Requirements Analyst Agent (`agents/requirements.py`)

**Class:** `RequirementsAgent`

**Receives (AgentContext):**
- `project_brief`: free text from PM/BA
- `jira_project_key`: fetched existing Jira epics for context
- `existing_stories`: current Jira story titles + descriptions
- `policies`: acceptance criteria guidelines from `governance/policies/`

**Produces (AgentResult artifacts):**
- Gherkin user stories (Feature/Scenario/Given-When-Then format)
- Gap analysis document: what the brief covers vs. what is missing
- Acceptance criteria per story
- Jira epic + story JSON payload ready for create API

**Writes output to:**
- Jira: creates epics and stories via `integrations/jira/client.py`
- Artifact DB: stores Gherkin document as artifact version
- Confluence: creates/updates Requirements page in project space

---

### Architecture Agent (`agents/architecture.py`)

**Class:** `ArchitectureAgent`

**Receives (AgentContext):**
- Requirements artifacts (from artifact DB, phase=requirements)
- Project tech stack + team size from `projects` record
- Existing ADRs from Confluence (fetched at run time)
- CLAUDE.md template from `claude-templates/` matching project type

**Produces (AgentResult artifacts):**
- Architecture Decision Records (ADR-NNN format, one per decision)
- Project CLAUDE.md (tailored to the target project)
- Component diagram (Mermaid `graph LR` or `C4Context`)
- Tech debt register (Markdown table with priority + owner columns)

**Writes output to:**
- Confluence: creates pages in ADR space
- GitHub: writes project CLAUDE.md via `PUT /repos/{owner}/{repo}/contents/CLAUDE.md`
- Artifact DB: all outputs stored as artifact versions with S3 keys

---

### PR Reviewer Agent (`agents/development.py`)

**Class:** `PRReviewerAgent`

**Receives (AgentContext):**
- GitHub PR diff: files changed, hunks (fetched from GitHub API)
- PR description + linked Jira story key
- Project CLAUDE.md (coding standards context, fetched from GitHub)
- Recent test coverage summary (if available in CI artifacts)

**Produces (AgentResult artifacts):**
- Inline PR review comments (per file + line range, GitHub review format)
- PR summary: complexity score, risk areas, suggested additional tests
- Code quality report: style issues, pattern violations, security flags

**Writes output to:**
- GitHub: inline review comments via `POST /repos/{owner}/{repo}/pulls/{number}/reviews`
- Artifact DB: quality report stored as artifact version

---

### QA Analyst Agent (`agents/testing.py`)

**Class:** `QAAnalystAgent`

**Receives (AgentContext):**
- User stories from Requirements phase (from artifact DB or Jira)
- Existing test file list from GitHub repo tree
- Coverage report if available (lcov.info or JSON from CI)

**Produces (AgentResult artifacts):**
- Test plan document (scope, approach, entry/exit criteria, environments)
- Test case suite (BDD-style, each mapped to a user story)
- Coverage gap analysis (code paths not covered by existing tests)
- QA checklist (pre-release sign-off items)

**Writes output to:**
- Confluence: QA space pages
- Jira: test task issues linked to parent stories
- Artifact DB: all documents stored with S3 keys

---

### Release Engineer Agent (`agents/cicd.py`)

**Class:** `ReleaseEngineerAgent`

**Receives (AgentContext):**
- GitHub tag name + commit range since last tag
- Jira stories resolved in this release cycle (by fix version)
- Deployment environment config from `project_integrations`

**Produces (AgentResult artifacts):**
- Release notes (user-facing changelog grouped by story type: feature/fix/chore)
- Deployment checklist (ordered environment-specific steps)
- Rollback plan (per service, with specific commands)
- Environment diff (configuration changes from previous release)

**Writes output to:**
- GitHub: release body via `POST /repos/{owner}/{repo}/releases`
- Confluence: release page in project space
- Artifact DB

---

### Technical Writer Agent (`agents/docs.py`)

**Class:** `TechWriterAgent`

**Receives (AgentContext):**
- OpenAPI schema from FastAPI `/openapi.json` endpoint
- Current project README from GitHub
- Confluence space structure for the project

**Produces (AgentResult artifacts):**
- API reference narrative (plain-language description per endpoint)
- Confluence onboarding guide (new developer setup walkthrough)
- README update (adds badges, quick start, architecture section)
- Changelog (assembled from git log + Jira story titles)

**Writes output to:**
- Confluence: docs space pages
- GitHub: README.md via file update API
- Artifact DB

---

### Compliance Officer Agent (`agents/governance.py`)

**Class:** `ComplianceOfficerAgent`

**Receives (AgentContext):**
- `audit_log` entries for the project (filtered by date range)
- `pii_events` for the project
- `policy_violations` for the project
- ARB submission template from `governance/policies/`

**Produces (AgentResult artifacts):**
- Audit report (AI usage summary, cost breakdown by model and phase)
- ARB prep document (architecture change summary, risk assessment, approval request in Markdown)
- Risk register update (identified risks, owners, mitigations, residual risk)
- PII event log formatted for CISO review
- Policy compliance matrix (policy → current status → evidence links)

**Writes output to:**
- Confluence: governance space pages
- Artifact DB (ARB approval recorded in audit_log by human approver action)

---

## API Design Principles

- All routes under `/api/v1/` — never remove or change the version prefix
- Errors use RFC 7807 Problem Details (`Content-Type: application/problem+json`):
  ```json
  {"type": "https://apex.example.com/errors/not-found", "title": "Project not found", "status": 404, "detail": "Project abc123 does not exist.", "instance": "/api/v1/projects/abc123"}
  ```
- 404s always return Problem Details — never an empty body
- Pagination: `?page=1&page_size=20`; response envelope: `{"total": N, "page": 1, "page_size": 20, "items": [...]}`
- Timestamps: always UTC, ISO 8601 (`2024-01-15T10:30:00Z`)
- IDs: UUIDs for all public-facing resources; no integer IDs in API responses
- OpenAPI docs at `/docs` (Swagger UI) and `/redoc` — keep accurate, add examples to schemas
- Webhooks (GitHub): verify `X-Hub-Signature-256` with HMAC-SHA256 before any processing

---

## Non-Negotiables (Golden Rules)

These rules come from eeik-bootstrap standards and must never be violated:

1. **Constructor injection via FastAPI DI** — never instantiate services inside route handlers. Use `Depends()` for all service injection.
2. **No hardcoded secrets** — all credentials via environment variables loaded through `core/config.py` (Pydantic BaseSettings). No secrets in code, no secrets in logs.
3. **Structured logging via structlog** — never use `print()` or bare `logging.info()`. Always `log.info("event_name", key=value, key2=value2)`.
4. **No `SELECT *`** — always specify columns explicitly in SQLAlchemy queries. Use `select(Model.col1, Model.col2)` or `select(Model)` with explicit `selectinload`.
5. **Parameterised queries only** — never string-format SQL. Use SQLAlchemy core expressions or ORM. Raw SQL via `text()` is banned.
6. **Pydantic v2 only** — use `model_validate()`, `model_dump()`, `model_config`. Do not use deprecated v1 APIs (`parse_obj`, `dict()`, `class Config`).
7. **No ORM lazy loading** — configure `lazy="raise"` on all relationships. Use `selectinload()` or `joinedload()` explicitly in queries.
8. **Async throughout** — all DB calls, HTTP calls, and agent I/O must use `async/await`. No synchronous blocking in async context (no `requests`, no `time.sleep`).
9. **PII guard on all agent I/O** — every string passed to or returned from Claude must pass through `middleware/pii_guard.py` before use.
10. **Every agent run logged** — `audit_log` entry created before agent starts; updated with result, token count, and cost after completion. Agent run without audit entry is a bug.

---

## Security

- **PII Guard** (`middleware/pii_guard.py`): runs on every agent input and output. Detects PII using regex patterns from `governance/pii-guard/patterns.py`. Redacts before sending to Claude API. Writes `pii_events` records for every detection event.
- **Audit log**: every agent invocation creates an `agent_runs` record (actor, model, phase, cost_usd) and an `audit_log` record (before/after artifact state). Append-only — no UPDATE or DELETE on `audit_log` table.
- **JWT authentication** (Phase 5): `middleware/auth.py` validates Bearer token on all routes except `/health`, `/docs`, `/redoc`, `/openapi.json`. Claims: `sub` (user ID), `org_id`, `persona` (role enum).
- **RBAC per persona**: Governance routes require `CISO` or `Lead` persona. Agent trigger endpoints require appropriate persona for the phase (e.g., Requirements agent requires `BA` or `Lead`).
- **Integration credentials**: stored in AWS Secrets Manager (cloud) or `.env` (local). Never logged. Never returned in API responses.
- **Webhook verification**: GitHub `X-Hub-Signature-256` verified with HMAC-SHA256 before any processing. Return 401 on invalid signature.
- **S3 artifacts**: SSE-S3 encryption, no public access, bucket policy blocks all public ACLs.

---

## Testing Standards

- **Framework**: pytest + pytest-asyncio; `asyncio_mode = "auto"` in `pyproject.toml`; all test functions `async def test_*`
- **API tests**: use `httpx.AsyncClient(app=app, base_url="http://test")` — no real network calls
- **DB tests**: separate test database (`apex_platform_test`); transaction rollback after each test using savepoints
- **Fixtures**: factory-boy factories for all ORM models in `tests/conftest.py`; define one factory per model
- **Mocking**: mock Anthropic API calls with `pytest-mock`; store fixture responses in `tests/fixtures/anthropic/{agent_name}.json`
- **Coverage**: minimum 80% line coverage; enforced in CI with `pytest --cov=app --cov-fail-under=80`
- **Agent tests**: unit test each agent class with mocked Claude streaming responses; verify PII guard and audit log are called

---

## Integration Specifications

### GitHub (REST API v3)

- Client: `integrations/github/client.py` using `httpx.AsyncClient`
- Auth: `Authorization: Bearer <GITHUB_TOKEN>` (fine-grained PAT or GitHub App token)
- Key endpoints: `GET /repos/{owner}/{repo}`, `GET /repos/{owner}/{repo}/pulls`, `POST /repos/{owner}/{repo}/pulls/{number}/reviews`, `PUT /repos/{owner}/{repo}/contents/{path}`, `POST /repos/{owner}/{repo}/releases`
- Webhooks: `X-Hub-Signature-256` verified; events handled: `pull_request`, `push`, `release`
- Rate limit: 5000 req/hr authenticated; implement exponential backoff with jitter on 429/403

### Jira (Agile REST API v1 + REST API v3)

- Client: `integrations/jira/client.py` using `httpx.AsyncClient`
- Auth: Basic `{JIRA_EMAIL}:{JIRA_API_TOKEN}` base64 encoded in `Authorization` header
- Base URLs: `{JIRA_BASE_URL}/rest/agile/1.0/` for boards/sprints; `{JIRA_BASE_URL}/rest/api/3/` for issue CRUD
- Key endpoints: `GET /board/{boardId}/sprint`, `GET /sprint/{id}/issue`, `POST /issue` (create story), `POST /issue/{id}/remotelink`
- Story creation: look up issue type IDs from project config; store in `project_integrations.config` JSONB

### Confluence (REST API v2)

- Client: `integrations/confluence/client.py` using `httpx.AsyncClient`
- Auth: Basic `{CONFLUENCE_EMAIL}:{CONFLUENCE_TOKEN}`
- Base URL: `{CONFLUENCE_BASE_URL}/wiki/api/v2/`
- Key endpoints: `GET /spaces`, `GET /pages?spaceId={id}&title={title}`, `POST /pages`, `PUT /pages/{id}`
- Page body: Confluence storage format (XHTML). Use `pypandoc` to convert Markdown → XHTML when needed.
- Versioning: `PUT /pages/{id}` requires `version.number` incremented; always fetch current version first

### Anthropic API (claude-opus-4-8)

- SDK: `anthropic` Python package (official Anthropic SDK)
- Client: `integrations/anthropic/client.py` wraps `anthropic.AsyncAnthropic`
- All agents use `client.messages.stream()` for streaming responses; emit SSE events per chunk
- System prompt: loaded from `prompts/{phase}/system.md` via `prompt_loader.py`; supports template variables
- PII guard runs BEFORE passing any content to the API; also runs on each streamed response chunk before storing
- Token accounting: capture `usage.input_tokens` and `usage.output_tokens` from final stream event; store in `agent_runs`
- Cost tracking: apply published per-model pricing to token counts; store `cost_usd` (Decimal) in `agent_runs`
- Error handling: catch `anthropic.APIStatusError` (check `.status_code`), `anthropic.RateLimitError` (retry with exponential backoff + jitter, max 3 retries), `anthropic.APIConnectionError` (retry once, then fail)
