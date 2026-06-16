# APEX Platform — Backend (FastAPI)

## Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.12 |
| Framework | FastAPI 0.115+ |
| Validation | Pydantic v2 (`model_validate`, `model_dump`) |
| ORM | SQLAlchemy 2.x async (`AsyncSession`) |
| Migrations | Alembic (`alembic revision --autogenerate`) |
| Database | PostgreSQL 16 |
| Task queue | Celery 5 + Redis 7 broker |
| Logging | structlog (JSON format in production) |
| HTTP client | httpx async |
| AI SDK | anthropic (official Python SDK) |
| Testing | pytest, pytest-asyncio, httpx, factory-boy, pytest-mock |

## Directory Layout

```
backend/
  app/
    api/
      v1/
        __init__.py
        router.py             master router — includes all sub-routers
        organisations.py      GET /organisations, POST, GET /{id}, PATCH /{id}
        projects.py           Full CRUD + GET /{id}/phases overview
        phases.py             GET /{projectId}/phases/{phase}, GET gate status
        artifacts.py          GET list, GET /{id}, GET /{id}/versions, GET /{id}/download-url
        agents.py             POST /{projectId}/phases/{phase}/agents/run, GET /{runId}/stream (SSE)
        governance.py         GET audit-log, GET pii-events, GET policy-violations
        auth.py               POST /auth/login, POST /auth/refresh (Phase 5)
    agents/
      base.py                 AgentContext dataclass, AgentResult dataclass, BaseAgent ABC
      orchestrator.py         Celery task wrapper, SSE event emitter, run lifecycle
      requirements.py         RequirementsAgent — Gherkin stories, gap analysis, Jira write
      architecture.py         ArchitectureAgent — ADRs, project CLAUDE.md, Mermaid diagrams
      development.py          PRReviewerAgent — inline PR comments, quality report
      testing.py              QAAnalystAgent — test plan, test cases, coverage gap analysis
      cicd.py                 ReleaseEngineerAgent — release notes, deployment checklist
      docs.py                 TechWriterAgent — API reference, onboarding guide, README
      governance.py           ComplianceOfficerAgent — audit report, ARB prep, risk register
    integrations/
      github/
        client.py             Authenticated httpx.AsyncClient; HMAC webhook verification
        prs.py                List PRs, fetch diff, post inline review comments
        releases.py           Create/update GitHub Release body
        repos.py              File read/write via GitHub contents API (CLAUDE.md writes)
        webhooks.py           pull_request + push event dispatch
      jira/
        client.py             Jira Agile REST v1 + REST API v3 wrapper (absorbs automation/jira-bridge/)
        sprints.py            Active sprint, sprint issues by board
        stories.py            Create epic, create story, update status, add remote link
        webhooks.py           Jira webhook receiver
      confluence/
        client.py             Confluence REST API v2 client (absorbs automation/confluence-writer/)
        pages.py              Create page, update page with version bump, get space pages
      anthropic/
        client.py             AsyncAnthropic wrapper — streaming, retry, token accounting
        tools.py              Tool definitions for GitHub/Jira/Confluence tool use
        prompt_loader.py      Loads system prompts from /prompts/{phase}/system.md
    middleware/
      pii_guard/
        guard.py              FastAPI middleware; scans all agent I/O (absorbs governance/pii-guard/guard.py)
        patterns.py           PII regex patterns (absorbs governance/pii-guard/patterns.py)
      audit.py                Writes audit_log entry for every agent invocation
      auth.py                 JWT RS256 Bearer token validation (Phase 5)
      correlation.py          Injects X-Correlation-ID on every request; binds to structlog context
    models/
      organisation.py         Organisation ORM model
      project.py              Project + ProjectIntegration ORM models
      team.py                 Team + Member ORM models
      phase.py                Phase + PhaseGate ORM models
      artifact.py             Artifact + ArtifactVersion ORM models
      agent_run.py            AgentRun + AgentRunMessage ORM models
      audit.py                AuditLog + PiiEvent + PolicyViolation ORM models
    schemas/
      organisation.py         OrganisationCreate, OrganisationRead Pydantic v2 schemas
      project.py              ProjectCreate, ProjectRead, ProjectUpdate schemas
      phase.py                PhaseRead, GateEvaluationRequest, GateEvaluationResult schemas
      artifact.py             ArtifactRead, ArtifactVersionRead, ArtifactDownloadUrl schemas
      agent_run.py            AgentRunCreate, AgentRunRead, AgentProgress, TokenUsage schemas
      governance.py           AuditLogRead, PiiEventRead, PolicyViolationRead schemas
      common.py               PaginatedResponse[T], ProblemDetail (RFC 7807), TimestampMixin
    services/
      organisation_service.py  Org CRUD, member management
      project_service.py       Project CRUD, integration config, phase orchestration
      phase_service.py         Phase state machine, gate evaluation, transition logic
      artifact_service.py      Artifact CRUD, S3 upload, pre-signed URL generation, versioning
      agent_service.py         Dispatch Celery task, manage run lifecycle, SSE stream emission
    db/
      session.py               AsyncEngine init, AsyncSessionLocal factory, get_db dependency
      base.py                  DeclarativeBase, TimestampMixin (created_at, updated_at)
      migrations/              Alembic versions/
    core/
      config.py                Settings class (pydantic-settings BaseSettings, reads .env)
      logging.py               structlog processor chain (JSON prod, key-value dev)
      security.py              JWT encode/decode, password hashing (Phase 5)
      storage.py               S3 boto3 async wrapper: upload, pre-signed URL, lifecycle tag
  tasks/
    celery_app.py              Celery app init, beat schedule config
    agent_tasks.py             run_agent_task(run_id, agent_type, context_dict) Celery task
    refresh_tasks.py           Periodic: refresh GitHub + Jira data per project
  tests/
    conftest.py                Async engine, test DB, httpx.AsyncClient, base fixtures
    factories/                 factory_boy factories for every ORM model
    api/                       Router integration tests — one file per router
    agents/                    Agent unit tests — mocked Claude API streaming responses
    integrations/              GitHub/Jira/Confluence client tests with VCR cassettes
    services/                  Service layer unit tests
  alembic.ini
  pyproject.toml
  Dockerfile
  .env.example
```

## Router Specifications

| Router file | Resource | Key endpoints |
|------------|---------|--------------|
| `organisations.py` | Organisations | `GET /organisations`, `POST /organisations`, `GET /organisations/{id}`, `PATCH /organisations/{id}` |
| `projects.py` | Projects | `GET /projects`, `POST /projects`, `GET /projects/{id}`, `PATCH /projects/{id}`, `DELETE /projects/{id}` |
| `phases.py` | Phases | `GET /projects/{id}/phases`, `GET /projects/{id}/phases/{phase}`, `POST /projects/{id}/phases/{phase}/gate/evaluate` |
| `artifacts.py` | Artifacts | `GET /projects/{id}/phases/{phase}/artifacts`, `GET /artifacts/{id}`, `GET /artifacts/{id}/versions`, `GET /artifacts/{id}/download` |
| `agents.py` | Agent runs | `POST /projects/{id}/phases/{phase}/agents/run`, `GET /agents/{runId}`, `GET /agents/{runId}/stream` (SSE) |
| `governance.py` | Governance | `GET /governance/audit-log`, `GET /governance/pii-events`, `GET /governance/policy-violations`, `GET /governance/gate-matrix` |

## Agent Implementation Pattern

Each agent is a class implementing `BaseAgent`:

```python
# app/agents/base.py
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID
from typing import Any, Literal

@dataclass
class AgentContext:
    project_id: UUID
    phase: str                          # "requirements" | "architecture" | etc.
    actor_id: str                       # user ID triggering the run
    inputs: dict[str, Any]             # phase-specific context (brief, diff, etc.)
    prompt_library: dict[str, str]     # loaded from prompts/{phase}/system.md
    run_id: UUID                       # pre-created agent_run record ID

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int

@dataclass
class AgentResult:
    run_id: UUID
    status: Literal["completed", "failed"]
    artifacts: list[dict]              # ArtifactCreate dicts
    token_usage: TokenUsage
    cost_usd: Decimal
    error: str | None = None

class BaseAgent:
    async def run(self, context: AgentContext) -> AgentResult: ...
```

Agent classes run as Celery tasks dispatched by `agent_service.py`:

```python
# tasks/agent_tasks.py
@celery_app.task(bind=True, max_retries=3)
def run_agent_task(self, run_id: str, agent_type: str, context_dict: dict):
    # Reconstruct AgentContext, instantiate agent class, call agent.run()
    # On completion: store result, emit SSE completion event
```

## SSE Stream Pattern

```python
# app/api/v1/agents.py
@router.get("/agents/{run_id}/stream")
async def stream_agent_progress(run_id: UUID, db: AsyncSession = Depends(get_db)):
    async def event_generator():
        async for message in agent_service.stream_run(db, run_id):
            yield f"data: {message.model_dump_json()}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## RFC 7807 Error Pattern

```python
# Never raise raw HTTPException with a plain string detail
# Always use the ProblemDetail schema from schemas/common.py
raise HTTPException(
    status_code=404,
    detail={
        "type": "https://apex-sdlc/errors/project-not-found",
        "title": "Project Not Found",
        "status": 404,
        "detail": f"No project with id={project_id} exists in this organisation.",
        "instance": f"/api/v1/projects/{project_id}",
    },
)
```

## Key Environment Variables

All loaded via `core/config.py` (pydantic-settings `BaseSettings`). Required in `.env`:

```
DATABASE_URL=postgresql+asyncpg://apex:apex_dev@localhost:5432/apex_platform
REDIS_URL=redis://localhost:6379/0
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
JIRA_BASE_URL=https://myorg.atlassian.net
JIRA_EMAIL=service@myorg.com
JIRA_API_TOKEN=...
CONFLUENCE_BASE_URL=https://myorg.atlassian.net
CONFLUENCE_TOKEN=...
S3_ARTIFACT_BUCKET=apex-artifacts-dev
AWS_REGION=eu-west-1
SECRET_KEY=random-64-char-string-for-jwt
ENVIRONMENT=development
LOG_LEVEL=INFO
```

Never access environment variables directly (`os.environ.get`). Always go through `core/config.py`:

```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    anthropic_api_key: str
    github_token: str
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    confluence_base_url: str
    confluence_token: str
    s3_artifact_bucket: str
    aws_region: str = "eu-west-1"
    secret_key: str
    environment: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "case_sensitive": False}

settings = Settings()
```

## Non-Negotiables

- `async/await` everywhere — no sync SQLAlchemy calls (`session.execute` must be `await session.execute`), no sync `requests`, no `time.sleep`
- No lazy loading — configure `lazy="raise"` on all relationships; always `selectinload()` / `joinedload()` in queries
- Pydantic v2 API — `model_validate(data)` not `Model(**data)` for untrusted input; `model_dump()` not `.dict()`; `@model_validator` not `@validator`
- PII guard runs before every Claude API call — enforced in `integrations/anthropic/client.py`; not optional
- Every agent run creates an `audit_log` entry — enforced in `agent_service.py`; agent run without audit entry is a bug
- No `print()` — structlog only: `log = structlog.get_logger(); log.info("event", key=value)`
- No raw SQL string formatting — SQLAlchemy ORM or `text()` with `:param` named binding
- No `SELECT *` — always `select(Model)` with explicit `selectinload` or `select(Model.col1, Model.col2)`
- FastAPI `Depends()` for all service injection — no module-level singleton service instances called directly in handlers

## Testing Pattern

```python
# tests/api/test_projects.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_project(async_client: AsyncClient, db_session):
    payload = ProjectFactory.build_dict(exclude={"id", "created_at", "updated_at"})
    response = await async_client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]

@pytest.mark.asyncio
async def test_project_not_found_returns_problem_detail(async_client: AsyncClient):
    response = await async_client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == 404
    assert "type" in body          # RFC 7807
```

Run tests:
```bash
pytest --cov=app --cov-fail-under=80 -v
```

## eeik Agents for This Directory

| Task | eeik Command |
|------|-------------|
| Implement a new router | "Using python-developer agent, implement the phases router with gate evaluation endpoint per the CLAUDE.md spec" |
| Add Alembic migration | "Using dba-advisor agent, generate Alembic migration for the artifact_versions table as described in platform/CLAUDE.md" |
| Implement an agent class | "Using ai-engineer agent, implement RequirementsAgent in agents/requirements.py using BaseAgent pattern from agents/base.py" |
| Design a new entity | "Using dba-advisor agent, design the schema for project_integrations JSONB config storage" |
| Review before PR | `/review` |
| Security check middleware | "Using devsecops-engineer agent, review the PII guard middleware implementation" |
| Estimate effort | `/estimate "implement all 7 agent classes"` |
