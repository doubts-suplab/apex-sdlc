# APEX Platform — Progress

An honest, increment-by-increment view of what is **built** vs **planned**. Newest first. This tracker
deliberately separates *structure* (the seams exist and are governed) from *substance* (real generation,
write-back, persistence, gates) so the [ROADMAP](../ROADMAP.md) and the code never drift apart.

Legend: ✅ done · 🚧 partial · ❌ not started

---

## Increment 21 — Phase 2: resolve an inbound event to the owning APEX project 🚧

The event → project → phase-agent chain is now complete: a webhook says *what happened*, the dispatch
router says *which phase reacts*, and this resolves *which registered project it concerns*.

- ✅ **`ProjectService.get_by_github_repo(repo)`** looks the project up by its `github_repo` column
  (case-insensitive — GitHub slugs are; empty repo → `None`, never a spurious match).
- ✅ The GitHub receiver now takes a DB session and returns a compact `project` reference
  (`{id, slug, name}`) alongside `event` + `dispatch`, or `null` when the repo matches no project. The
  Jira receiver returns the same key (currently always `null` — a jira-project-key column is still
  pending), so a consumer treats both uniformly.
- ✅ 3 DB-backed tests (seeded project resolved, case-insensitive match, unknown repo → `null`), verified
  offline via aiosqlite. **162 total green;** `examples/` byte-identical.
- ❌ **Not yet:** Jira project resolution (needs a jira-project-key column), and actually enqueuing the
  dispatched agent run for the resolved project.

## Increment 20 — Phase 2: webhook → phase-agent dispatch router 🚧

The inbound event now routes to the SDLC phase whose agent should react — the seam a background worker
consumes to enqueue an agent run.

- ✅ **`integrations/dispatch.py`** maps a normalized event to a `WebhookDispatch(phase, agent, persona,
  reason)` drawn straight from the phase catalog (so it can never name an agent the platform doesn't run):
  a GitHub `pull_request` opened/reopened/synchronize → **Development** (PR review), a `release` published
  → **CI/CD** (release artifacts), a Jira `Story`/`Epic`/`Task` created/updated → **Requirements** (refresh).
  Noise (a `labeled` PR, a `push`, a Jira comment, a `Sub-task`) routes to **nothing**.
- ✅ **Governed posture, mirrored:** the router only *proposes* — it holds no authority. The harness
  confidence gate still decides auto-enforcement and the default-deny tool registry still governs side
  effects; the mapping is transparent so the routing is auditable (structlog `dispatch=<phase>`).
- ✅ Both webhook endpoints now return `dispatch` alongside the parsed event.
- ✅ 9 dispatch tests + endpoint assertion. **159 total green;** `examples/` byte-identical.
- ❌ **Not yet:** actually enqueuing/running the dispatched agent (needs the Celery path + a configured
  provider), and event de-dup/idempotency.

## Increment 19 — Phase 2: signature-verified webhook receivers (GitHub + Jira) 🚧

Inbound events now have a governed entry point — the seam a background dispatcher/agent reacts to.

- ✅ **GitHub receiver** `POST /api/v1/webhooks/github`: reads the raw body, verifies the
  `X-Hub-Signature-256` HMAC-SHA256 against `GITHUB_WEBHOOK_SECRET` **before any processing** (platform
  security rule), returns **401** on a missing/malformed/mismatched signature, then normalizes
  `pull_request` / `push` / `release` into a compact `{event, repo, action, summary, …}`.
- ✅ **Jira receiver** `POST /api/v1/webhooks/jira`: optional shared-secret check (empty configured secret
  → accept, dev mode; mismatch → 401), normalizes the `webhookEvent` discriminator into
  `{event, issue_key, issue_type, status, summary}`.
- ✅ Pure, offline-testable verification + normalization in `integrations/github/webhooks.py` and
  `integrations/jira/webhooks.py`; config gains `GITHUB_WEBHOOK_SECRET` + `JIRA_WEBHOOK_SECRET`.
- ✅ 12 tests (`tests/api/test_webhooks.py`): valid/tampered/malformed signatures, event parsing for all
  three GitHub events + Jira, endpoint 200/401 paths. **150 total green;** `examples/` byte-identical.
- ✅ **Event → agent routing now built** (Increment 20: `pull_request` → PR-review, `release` → CI/CD,
  Jira Story → Requirements). ❌ **Not yet:** actually running the dispatched agent, and delivery
  retry/idempotency (event de-dup).

## Increment 18 — Phase 0: full repo-tree emission + GitHub bootstrap 🚧

Onboarding now emits an **actual scaffolded repository** (files), not just a plan — the core remaining
Phase 0 deliverable.

- ✅ **`repo_generator.generate_repo_tree()`** turns an onboarding result into a `{path: content}` tree:
  a stack-appropriate skeleton (**Java/Spring Boot** — `pom.xml` + a `@SpringBootApplication` main +
  DDD `domain/application/infrastructure/web` layers + a `@SpringBootTest`; **Python/FastAPI** —
  `pyproject.toml` + `app/main.py` with a `/health` route + `tests/`), plus `CLAUDE.md`, the normalized
  manifest, `README.md`, `.gitignore`, and a CI workflow. Deterministic, offline, byte-reproducible.
- ✅ **GitHub bootstrap:** `repo_bootstrap.bootstrap_plan()` gives an offline dry-run (repo + files that
  *would* be created); `push_repo_tree()` + new `GitHubClient.create_repository`/`put_file` are the
  credentialed swap-in (create repo → commit each file).
- ✅ API `POST /api/v1/onboarding/repo-tree` returns the tree + bootstrap plan; demo
  `python -m app.demo.generate_repo` → `examples/generated-repo/<slug>/` (a full committed Java repo).
- ✅ 5 tests (`tests/onboarding/test_repo_generator.py`): common files present, Java/Python skeletons,
  determinism, bootstrap-plan shape. **138 total green;** pre-existing `examples/` byte-identical.
- ❌ **Not yet:** actually creating the GitHub repo (credential-gated), and the eeik LLM-driven
  `repository-generator` for richer, input-tailored source (this is the deterministic stand-in).

## Increment 17 — Global auth middleware (opt-in, allowlist-based) 🚧

Closes Increment 8's "global auth enforcement" gap without breaking the offline demo.

- ✅ **`AuthMiddleware` (`app/middleware/auth.py`):** when `AUTH_REQUIRED=true`, every request needs a
  valid bearer token except an **allowlist** (`/health`, `/docs`, `/redoc`, `/openapi.json`,
  `/api/v1/auth/token`) — so login and health stay reachable. Invalid/missing → RFC-7807 401. The
  per-route `require_persona(...)` RBAC still layers on top (this enforces *authentication* only).
- ✅ **Off by default** (`AUTH_REQUIRED=false`) so the reference/onboarding/devops demo endpoints stay
  open and every existing test/demo is unaffected; production flips one env var to lock the surface.
- ✅ 4 tests (`tests/api/test_auth_middleware.py`): default-off leaves routes open; enforced → 401 without
  a token, 200 with, 401 on a bad token; health + `/auth/token` stay open under enforcement. **133 total
  green;** `examples/` byte-identical.
- ❌ **Not yet:** binding the token's persona to a project `Member` at request time (the mapping exists —
  Increment 16 — but isn't enforced), and refresh tokens.

## Increment 16 — Team & Member models (the last missing data-model tables) ✅

Adds the final two entities from the core data model, closing Increment 1's "missing models" list.

- ✅ **`Team`** (org-scoped, unique `slug` per org) and **`Member`** (`app/models/team.py`): a user with a
  **persona role** on a project (`persona` ∈ the catalog's seven), optionally via a team, unique per
  `(project, subject)`. This is the **persona↔identity mapping** the RBAC layer (Increment 8) referenced —
  a JWT `sub`+`persona` can now be reconciled against a project's members.
- ✅ **Migration `0002_add_teams_and_members.py`** chains off the baseline; the drift-guard test now runs
  `0001 → 0002` and still matches `Base.metadata` exactly.
- ✅ 2 model tests (`tests/models/test_team_member.py`): team + members persist with personas and the
  `(project, subject)` uniqueness constraint is enforced. **129 total green.**
- ❌ **Not yet:** a members CRUD API + onboarding seeding a default team, and enforcing that a token's
  persona matches a project member at request time (the mapping exists; wiring it into RBAC is the follow-on).

## Increment 15 — Alembic baseline migration (schema versioning) ✅

Closes the "no migrations" gap flagged in Increments 1 and 6 — the schema is now **versioned**, not just
built ad-hoc via `metadata.create_all`.

- ✅ **Baseline migration** (`app/db/migrations/versions/0001_initial_schema.py`) creates all 11 current
  tables (organisations, projects, project_integrations, phases, phase_gates, artifacts,
  artifact_versions, agent_runs, audit_log, pii_events, policy_violations) with their indexes and FKs;
  the Postgres `JSONB` variants are preserved (`sa.JSON().with_variant(JSONB, "postgresql")`).
- ✅ **`env.py` now sees every model** (imports the `app.models` package, not a stale subset) and reads
  the runtime `DATABASE_URL` — so `alembic upgrade head` works against production Postgres **or** SQLite.
- ✅ **Drift-guard test** (`tests/db/test_migrations.py`): runs the real migration against a throwaway
  SQLite file and asserts the created tables **exactly equal** `Base.metadata` (a model added without a
  migration, or vice-versa, fails CI), then `downgrade base` drops everything. **127 total green.**
- ❌ **Not yet:** switching the app/tests off `metadata.create_all` onto migrations as the sole schema
  source (the test suite still builds via `create_all` for speed; the migration is verified separately).

## Increment 14 — Governance persistence: audit_log · pii_events · policy_violations ✅

Completes a long-standing gap from Increments 1, 7, and 8: the governance tables now exist and are
**populated when a journey is persisted**, with a CISO-gated read API.

- ✅ **Models (`app/models/audit.py`):** `AuditLog` (append-only, one per AI action — golden rule #10),
  `PiiEvent` (a PII-guard detection: label · direction · action · occurrences), and `PolicyViolation`
  (severity + remediation status). Registered for Alembic discovery; portable JSON columns.
- ✅ **Populated in `persist_journey`:** every phase run writes an `AuditLog` (actor=persona, model,
  tokens, cost, after-summary); the agent now **accumulates PII findings** (`PhaseAgent._record_pii` →
  `AgentResult.pii_findings` → `JourneyPhase`, excluded from `journey.json` so `examples/` stay
  byte-identical) which persist as `PiiEvent` rows; a governance-phase ALERT/BLOCK or a failing gate
  becomes a `PolicyViolation`.
- ✅ **CISO/Lead read API:** `GET /projects/{id}/governance/{audit-log,pii-events,policy-violations}` —
  `require_persona("ciso","lead")` (anonymous → 401, other persona → 403). The persist summary now
  reports `audit_entries` / `pii_events` / `policy_violations`.
- ✅ Tests: the reference journey persists **7 audit rows**, **1 policy violation** (governance ALERT),
  and deterministic PII events; the governance API's 401/403/200 RBAC matrix. **126 total green;**
  `examples/` byte-identical.
- ❌ **Not yet:** append-only enforcement at the DB level (a trigger/permission blocking UPDATE/DELETE on
  `audit_log`), the AWS-Comprehend PII layer, and an ARB approval workflow.

## Increment 13 — Project cost dashboard wired to DB + frontend persona-login 🚧

The cost dashboard now works on a **persisted project's stored runs**, driven by a frontend auth flow.

- ✅ **Frontend persona-login (`lib/auth.ts`):** `useAuthToken()` mints a JWT for the active persona via
  `POST /auth/token` and registers it on `apiFetch` (module-level bearer). It re-mints on persona change,
  so authenticated calls carry the persona for RBAC — the first UI path that drives the auth endpoints.
- ✅ **Project dashboard on `/projects/{id}`:** `ProjectCostDashboard` reads the project's stored metering
  (`useProjectMetrics` → `GET /projects/{id}/metrics/cost-latency`) and offers a **"Run + persist journey"**
  action (`usePersistJourney` → `POST …/journey/persist`) that is **gated to approver personas** — a
  developer/qa/pm sees a disabled button with a hint; lead/ba/architect/ciso can run it. On success the
  dashboard refreshes.
- ✅ **Re-priceable DB endpoint:** `GET /projects/{id}/metrics/cost-latency?model=<id>` re-prices the stored
  token counts illustratively (the UI passes `claude-opus-4-8`), so a stub-metered ($0) project still shows
  meaningful dollars; default is the actual recorded cost.
- ✅ `CostDashboard` refactored into a shared presentational `MetricsPanel` (loading/error/empty states) +
  a reference container (`/journey`, unchanged) and the new project container. `apiFetch` now unwraps both
  flat and `detail`-nested RFC-7807 errors.
- ✅ Backend re-pricing test (persist → `$0` actual, non-zero at a reference model); frontend
  `tsc --noEmit` + `next build` clean; `examples/` byte-identical; **123 backend tests green**.
- ❌ **Not yet:** a real credential login (this is still the persona identity-broker), an org-level
  cross-project cost roll-up, and streaming live agent runs (SSE) into the UI.

## Increment 12 — Cost dashboard UI + offline reference-metrics endpoint 🚧

The per-persona metering now has a **live front-end** and an offline API to feed it.

- ✅ **Offline endpoint:** `GET /api/v1/journey/reference/metrics?model=<id>` aggregates the reference
  journey's metering per persona (`app/agents/metrics.py::metrics_by_persona`) — real token counts +
  latency, with an **illustrative `cost_usd`** priced at a reference model (default `claude-opus-4-8`)
  so the offline demo shows meaningful dollars. No DB/auth, mirroring `/journey/reference`.
- ✅ **Frontend dashboard:** a `CostDashboard` component on `/journey` (TanStack Query hook
  `useReferenceMetrics` + Zod `ReferenceMetrics` schema) renders a **per-persona table** (runs, tokens
  in/out, est. cost, avg latency) with totals, and **highlights the active persona** from the switcher.
- ✅ 4 tests (`test_journey.py` aggregation + `tests/api/test_journey_metrics.py`): deterministic
  per-persona tokens/cost, developer-owns-two-phases, model override, and the "actual" (no-pricing) path.
  Frontend `tsc --noEmit` + `next build` clean; `examples/` byte-identical. Test env now pins
  `LLM_PROVIDER=stub` so API-driven journeys meter deterministically. **123 total green.**
- ❌ **Not yet:** wiring the dashboard to a **persisted project's** DB metrics
  (`GET /projects/{id}/metrics/cost-latency`, which needs auth + a stored journey) and time-series rollups.

## Increment 11 — Cost / token / latency metering, per-persona dashboard 🚧

Every agent run is now **metered**, and the platform aggregates cost, tokens, and latency **per persona**.

- ✅ **Per-run capture:** `PhaseAgent.complete()` accumulates input/output tokens and captures the
  model/provider across a run; `run_agent` times the harness invocation. Flows into `AgentResult` →
  `JourneyPhase` → the persisted `AgentRun` (new columns: `input_tokens`, `output_tokens`, `cost_usd`,
  `duration_ms`, `model`, `provider`).
- ✅ **Pricing (`app/agents/pricing.py`):** USD-per-1M-token table by model; unknown/`stub` models cost
  `$0`, so the offline journey meters deterministically at zero while a real provider yields real figures.
- ✅ **Determinism preserved:** metering rides in-memory on `JourneyPhase` but `JourneyResult.to_dict()`
  serializes only the stable subset — `journey.json` and all `examples/` stay **byte-identical**
  (`duration_ms` is wall-clock and never leaks in).
- ✅ **Dashboard:** `PersistenceService.cost_latency_by_persona()` maps each phase to its owning persona
  (catalog) and sums runs/tokens/cost + average latency; `GET /projects/{id}/metrics/cost-latency`
  serves it, and `GET …/agent-runs` now returns per-run metering.
- ✅ 7 tests (`tests/agents/test_metering.py` + persistence): pricing math, per-run capture, journey
  metering, the serialization-exclusion guard, and per-persona aggregation (developer owns 2 phases →
  2 runs). **124 total green.**
- ❌ **Not yet:** real per-run pricing eval (needs a live provider), a frontend dashboard view, and time-
  series/rollup storage.

## Increment 10 — Live, config-driven tool adapters (credentialed swap-in) 🚧

The DevOps tools can now run **against real systems**, selected per tool by configured credentials — the
offline set stays the default and the fallback.

- ✅ **Live adapters (`app/agents/tools/live_adapters.py`):** GitHub PR, Jira issue, Confluence page,
  Slack message, Jenkins build — each wraps an async integration client, bridges to the harness's sync
  tool call, and normalises to the same result shape as the offline adapter (drop-in).
- ✅ **Every endpoint is config/env-driven:** base URLs and tokens come from `Settings`
  (`GITHUB_API_BASE`, `SLACK_BASE_URL`/`SLACK_BOT_TOKEN`, `JENKINS_BASE_URL`/`JENKINS_USER`/
  `JENKINS_API_TOKEN`, plus the existing Jira/Confluence config), so a tool can point at the real API, a
  **mock server**, or a self-hosted instance with no code change. New `SlackClient` + `JenkinsClient`;
  `GitHubClient` gained a configurable `base_url` + `create_pull_request`.
- ✅ **`resolve_adapters(settings)`** picks live-vs-offline **per tool**: a system with credentials runs
  live, everything else stays offline — so a partially-configured env still runs end-to-end. The
  `POST /devops/flow` API uses it; the demo/tests stay fully offline and deterministic.
- ✅ 3 tests (`tests/devops/test_live_adapters.py`): offline fallback with no creds, a single tool
  flipping to live when configured, and a **live GitHub PR driven against an in-process mock transport**
  proving the configurable base URL is honoured (no real network). Test env is now **hermetic** —
  conftest clears ambient integration creds so no test reaches a live system. **112 total green.**
- ✅ **Webhook receivers now built** (Increment 19). ❌ **Not yet:** retry/backoff + rate-limit handling
  in the live adapters, and persisting each tool call to an audit table.

## Increment 9 — Governed DevOps tools: NL intent → multi-tool flow under the harness gate 🚧

The platform can now take a **natural-language DevOps request** and drive **multiple external tools**
(GitHub, Jira, Confluence, Slack, Jenkins) through the harness — the connective tissue for tool adapters,
the NL-intent flow, and spine→PR/ticket creation.

- ✅ **Tool catalog + registry (`app/agents/tools/`):** five named, typed write tools registered in the
  harness `ToolRegistry` with a **default-deny** allowlist (no wildcards; an ungranted tool or agent raises
  `ToolNotAuthorizedError` *before* any side effect). Offline, deterministic **adapters** stand in for the
  real systems; a credentialed adapter of the same name swaps in with no change above the registry.
- ✅ **NL-intent planner (`app/devops/intent.py`):** a transparent, deterministic keyword planner maps a
  free-text request to an ordered pipeline of tool calls (branch→PR→CI→ticket→docs→notify). It stands in
  for an LLM planner and returns the same `list[PlannedCall]` shape the real one will.
- ✅ **Harness-gated executor (`app/devops/flow.py`):** `DevOpsAgent` (authority `RATE_LIMIT`) ties side
  effects to the **confidence gate** — it executes the tools **only** when confidence clears the
  auto-enforce bar; a recognised-but-under-specified request is **held for human review** (SUGGEST, no side
  effects) and an unrecognised one **defers**. The agent never sets `auto_enforced`.
- ✅ API `POST /api/v1/devops/flow` (approver-persona RBAC) + demo `python -m app.demo.devops_flow` →
  `examples/devops-flow/` (executed / held-for-review / deferred). 14 tests (`tests/devops/` +
  `tests/api/test_devops.py`): adapter determinism, default-deny, intent ordering, and the three gated
  outcomes end-to-end. **109 total green.**
- ❌ **Not yet (credential-gated):** the real GitHub/Jira/Confluence/Slack/Jenkins adapters (network I/O
  behind the same tool names), an **LLM planner** replacing the keyword planner, and persisting the flow's
  runs/artifacts. The governance spine is real and offline-verifiable; the live wiring is the swap-in.

## Increment 8 — Auth & persona RBAC (ROADMAP Phase 5) 🚧

The platform now has an **identity + authorization** primitive: a bearer token carries a persona, and
persona-scoped RBAC guards a sensitive write.

- ✅ `app/core/security.py`: HS256 JWT issue/verify built on the **standard library** (`hmac`/`hashlib`) —
  no `pyjwt`/`python-jose`/`cryptography` dependency, so auth works in the offline test env and stays
  deterministic. Claims: `sub`, `persona` (one of the catalog's seven), optional `org_id`, `iat`/`exp`;
  constant-time signature check; expiry enforced. An RS256 signer can slot behind the same interface later.
- ✅ `POST /api/v1/auth/token` mints a token for a subject+persona (an honest **dev/identity-broker login** —
  no credential store yet); `GET /api/v1/auth/me` echoes the principal. `require_persona(...)` is a reusable
  FastAPI RBAC dependency returning RFC-7807 401/403.
- ✅ **Applied to the human-approval write:** `POST /projects/{id}/journey/persist` (which runs + approves a
  governed journey) now requires an **approver persona** (`lead`/`ba`/`architect`/`ciso`) — anonymous → 401,
  wrong persona → 403. Read endpoints stay open pending global enforcement.
- ✅ 11 tests (`tests/api/test_auth.py`): token round-trip, tampered/expired/malformed rejection, unknown
  persona rejected, token endpoint + `/me`, and the persist write's 401/403/200 RBAC matrix. **95 total
  green;** `examples/` byte-identical.
- ❌ **Not yet:** a real credential/user store (password/OIDC), **global** auth middleware on every route
  (only the persist write is guarded today), persona↔`Member` mapping, and token refresh.

## Increment 7 — PII guard on agent I/O (ROADMAP Phase 5, golden-rule gap) 🚧

The backend golden rule "PII guard on all agent I/O" is now **enforced in code**, not just a root script.

- ✅ A regex PII guard lives in the platform: `app/middleware/pii_guard/` (`patterns.py` + a regex-only
  `PiiGuard`). It's **offline and dependency-free** — the root copy's AWS Comprehend layer is intentionally
  left out so the guard stays deterministic and testable; a Comprehend adapter can slot in behind the same
  interface later.
- ✅ Wired into `PhaseAgent.complete()` (`app/agents/base.py`): **outgoing** prompts + system are
  **scrubbed** (PII never reaches the model); **incoming** completions are **scanned and logged** for the
  audit trail but returned intact (redacting model output would corrupt a legitimately generated artifact —
  the outbound boundary is the data-protection one).
- ✅ Fixed a latent bug absorbed from the root guard: overlapping matches (e.g. `SSN` vs `SORT_CODE`) no
  longer produce garbled double-redaction — the most-specific pattern claims a span first.
- ✅ 7 tests (`tests/middleware/test_pii_guard.py`): detect/redact email·SSN·card, clean-text passthrough,
  disabled passthrough, and a capturing-LLM test proving `complete()` scrubs outgoing PII and preserves
  incoming content. **84 total green.** `examples/` byte-identical (the offline stub carries no PII).
- ✅ **`pii_events` now persisted** (Increment 14): the guard's findings are captured on the agent and
  stored as `PiiEvent` rows during `persist_journey`, surfaced via the CISO governance API.
- ❌ **Not yet:** the Comprehend NLP layer (names/addresses), and the **physical** retirement of the root
  `governance/pii-guard/` copy + `automation/jira-bridge` — that path move is the dedicated
  [Phase 6 consolidation](../ROADMAP.md#phase-6--repo-consolidation--hardening-weeks-1718) increment
  (moving it now would churn imports mid-stream).

## Increment 6 — DB persistence (ROADMAP Phase 4) 🚧

A governed journey's outputs are now **stored, queryable state** instead of in-memory/ephemeral.

- ✅ New models `Artifact` (content + SHA-256 + version) and `AgentRun`; gates persist via the existing
  `Phase` + `PhaseGate` models. `PersistenceService.persist_journey()` stores every phase's run, artifacts,
  and gate; `list_artifacts` / `list_agent_runs` / `gate_matrix` read them back.
- ✅ API: `POST /projects/{id}/journey/persist` + `GET /projects/{id}/{artifacts,agent-runs,gate-status}`.
  Onboarding now **persists a Project** when an `organisation_id` is supplied.
- ✅ **Revived the dormant DB test suite:** made `ProjectIntegration.config` portable
  (`JSON().with_variant(JSONB, "postgresql")`) so the schema compiles on SQLite, and added `aiosqlite` —
  the previously-erroring 16 `tests/api` tests now pass. 5 new persistence tests (75 total green) verify a
  reference journey persists 17 artifacts / 7 runs / 7 gates and reads back.
- ✅ **Alembic baseline** now versions the schema (Increment 15). ❌ **Not yet:** S3 storage, and
  auth/RBAC on the read endpoints (the persist write is guarded — Increment 8).
- ✅ **Artifact version lineage:** an `ArtifactVersion` table + idempotent upsert — re-persisting unchanged
  content is a no-op; a content change bumps the artifact version and snapshots the prior content
  (`GET /projects/{id}/artifacts/{artifact_id}/versions`).

## Increment 5 — Real LLM generation path (ROADMAP Phase 3–4) 🚧

The phase agents now **generate their artifact bodies through the LLM port** instead of hard-coding them.

- ✅ `PhaseAgent.generate(prompt, fallback, system)` (`base.py`): a substantive completion is used verbatim;
  a short reply or any LLM failure falls back to the deterministic template. All seven agents route every
  artifact through it, with per-phase system prompts in `app/agents/prompts.py` and input-specific prompt
  builders in each agent.
- ✅ 3 tests (`tests/agents/test_generation.py`) prove a substantive completion reaches the artifact and a
  short reply falls back; 38 total green.
- ✅ **Offline is byte-identical.** With the `stub` provider the fallback templates are used, so the
  committed reference journey / gate report don't churn.
- 🚧 **Provider-gated:** real, input-driven artifacts require a configured provider
  (`LLM_PROVIDER=anthropic` + key). That path is wired and tested via a generative stub; **eval of real
  output quality** (and streaming into artifacts) is the follow-on.

## Increment 4 — Phase-gate engine (ROADMAP Phase 5) 🚧

The spec-driven spine is now **enforceable**: a phase can't advance until its gate passes.

- ✅ Pure, offline gate engine (`app/gates/`): `evaluate_gate` (a phase passes when its catalog-required
  artifacts are present, its spec is approved — auto-enforced decisions count; human-review specs need
  explicit approval — and the run had no confidence-gate bypass) and `evaluate_journey` (evaluates the whole
  spine, returning the first `blocking_phase`).
- ✅ API: `POST /api/v1/projects/{id}/phases/{phase}/gate/evaluate` and
  `GET /api/v1/journey/reference/gates?approved=<csv>`. Demo: `python -m app.demo.gate_report` →
  `examples/reference-project/gate-report.md`. 7 self-contained tests (35 total green).
- ✅ Frontend: gate badge per phase on `/journey` + an "Approve spec" toggle that unblocks the spine live.
- 🚧 Shows the spine blocking at **Requirements** with no approvals; clears once the human-review specs are
  approved.
- ❌ **Not yet:** DB persistence of gate evaluations (the `phase_gates` model is the target), a real
  approval/identity store, and the rest of Phase 5 (ARB workflow, mainframe-gate policy, CISO view, CDK).

## Increment 3 — Onboarding front door (eeik bridge, Phase 0) 🚧

The eeik→APEX bridge exists as a deterministic, offline transform.

- ✅ Onboarding core (`app/onboarding/`): a Pydantic `ProjectManifest` mirroring the eeik schema, a
  `capability_resolver` that reads the vendored `capability-matrix.yaml`, a deterministic `scaffold`
  generator (project `CLAUDE.md` + normalized manifest + scaffold plan), and a `service.onboard()` that
  registers the project at the **Requirements** phase.
- ✅ Vendored eeik onboarding data under `app/onboarding/eeik_assets/` (manifest schema, question sets,
  capability matrix, examples) with `PROVENANCE.md`.
- ✅ API (`/api/v1/onboarding/{questions,preview,}`), offline demo (`python -m app.demo.onboard_project` →
  `examples/onboarded-project/`), 8 self-contained tests, and a real frontend wizard (`/onboard`).
- ✅ **Consumes the real eeik engine (eeik v1.4).** `app/onboarding/eeik_engine.py` — an `EeikEngine` with
  two backends: **SDK** (`import eeik`, in-process) and **MCP** (spawns `eeik mcp`). `service.onboard_with_eeik()`
  validates the manifest against eeik's *canonical* schema and records eeik's authoritative pack resolution,
  falling back to the vendored path when eeik is absent. Demo `python -m app.demo.eeik_engine_demo` (sdk + mcp);
  6 tests (skip if eeik not installed). Consuming the live engine surfaced that the vendored `PROVENANCE`
  schema path was stale and that the Pydantic model can emit schema-invalid fields (both noted).
- ❌ **Not yet:** full compilable repo-tree emission + actually creating a GitHub repo (the LLM-driven eeik
  `repository-generator` path); persisting the onboarded project to the DB registry; reconciling
  `app/onboarding/manifest.py` (Pydantic) with eeik's canonical schema so `model_dump` always validates.

## Increment 2 — Harness-governed phase agents + reference journey ✅

The whole SDLC runs on the [agent-harness](https://github.com/doubts-suplab/agent-harness) (HALO), offline.

- ✅ All seven phase agents on the harness (`app/agents/`): Requirements, Architecture, Development, Testing,
  CI/CD, Docs, Governance — each a `PhaseAgent` that proposes a `Decision`; the harness owns enforcement.
- ✅ Persona/phase/agent **catalog** (single source of truth, `catalog.py`) + in-memory **orchestrator**
  that walks a project through all seven phases on one harness.
- ✅ Deterministic offline **stub LLM** (`LLM_PROVIDER=stub`); journey + agent-run API routes;
  `/journey` frontend view with persona filtering; committed reference project (17 artifacts).
- ✅ 20 governance tests green; `confidence_gate_bypass_total == 0`.
- 🚧 **Caveat — artifacts are templated, not yet LLM-generated.** Each agent emits deterministic content in
  `decide()`; the LLM writes only the one-line rationale. Turning this into *real* generation from real
  project input is the headline remaining work (see below).
- ❌ No write-back to Jira/Confluence/GitHub; no artifact persistence; no phase-gate enforcement.

## Increment 1 — Platform skeleton 🚧

The running shell exists; most of the data model and cross-cutting middleware do not.

- ✅ FastAPI app, correlation-ID middleware, health, structlog; org/project/integration registry API.
- ✅ Multi-provider LLM layer (`anthropic`, `ollama`, `groq`, `huggingface`, `stub`).
- ✅ Frontend shell: org home (project grid), project detail (SDLC timeline), integrations pages.
- ✅ ORM models now cover the **full core data model**: `organisation`, `project`, `integration`, `phase`,
  `phase_gate`, `artifact`, `artifact_version`, `agent_run`, `audit_log`, `pii_event`, `policy_violation`
  (Increment 14), and `team` + `member` (Increment 16).
- ✅ **Alembic baseline migration** now versions the schema (Increment 15). 🚧 PII-guard
  middleware scrubs/scans agent LLM I/O (Increment 7); 🚧 JWT + persona RBAC guards the persist write
  (Increment 8); ❌ audit middleware (only correlation) and global auth enforcement remain.

## Increment 0 — Framework & platform spec ✅

- ✅ Framework docs (`docs/APEX-Framework.md`), ROADMAP, master + backend + frontend `CLAUDE.md`, prompt
  library (all 7 personas), `docs/personas.md`, governance policies, HTML overview pages.

---

## Remaining — mapped to ROADMAP phases

| Capability | ROADMAP phase | Status |
|---|---|---|
| **Onboarding via eeik** — resolve packs + scaffold (`CLAUDE.md` + plan), enter the spine | [Phase 0](../ROADMAP.md#phase-0--onboarding-the-eeik-front-door) | 🚧 deterministic bridge built; full repo-tree emission + GitHub repo + DB persistence pending |
| **Real LLM generation** — model-generated specs from real input | Phase 3–4 | 🚧 path wired via `PhaseAgent.generate()` + prompts; real output needs a configured provider; quality-eval is the follow-on |
| **Live integrations** — GitHub/Jira/Confluence live data + background refresh | Phase 2 | 🚧 clients + config-driven live adapters (Increment 10) + signature-verified inbound webhooks (Increment 19) + event→phase-agent dispatch router (Increment 20) + event→owning-project resolution (Increment 21) built; background refresh + running the dispatched agent pending |
| **Agent write-back** — create Jira epics/stories, post GitHub PR reviews, publish Confluence | Phase 3 | 🚧 governed tool-call path built (Increment 9): default-deny registry + offline adapters, gated execution; real credentialed adapters pending |
| **DevOps tool flow** — NL intent → multi-tool pipeline (GitHub/Jira/Confluence/Slack/Jenkins) under the harness gate | Phase 3 | 🚧 offline flow built + verified (Increment 9); LLM planner + live adapters pending |
| **Dev repo bootstrap** — scaffold the actual service (eeik `repository-generator`) | Phase 0 / 3 | 🚧 deterministic repo-tree emission built (Increment 18); real GitHub repo creation + LLM generator pending |
| **Architect target-architecture** — reason over requirements + existing system → target-state ADR/C4 | Phase 4 | ❌ (templated ADR only today) |
| **Artifact persistence** — artifacts + agent runs + gates in DB, with version lineage | Phase 4 | 🚧 DB persistence + version lineage built (SQLite-verified); S3 storage pending; Alembic baseline built (Increment 15) |
| **Phase-gate engine** — enforce the spec-driven spine's phase transitions | Phase 5 | 🚧 pure engine + API + UI built offline; DB persistence + approval store pending |
| **PII guard on agent I/O** — regex scrub outgoing / scan+log incoming on every LLM call | Phase 5 | 🚧 middleware built + wired (Increment 7); `pii_events` persistence + Comprehend NLP layer pending |
| **Governance persistence** — audit_log, pii_events, policy_violations tables + CISO view + ARB | Phase 5 | 🚧 tables + population during persist + CISO-gated read API built (Increment 14); append-only DB enforcement + ARB workflow pending |
| **Auth & RBAC** — JWT, persona-scoped access | Phase 5 | 🚧 HS256 JWT + `require_persona` built (Increment 8), guarding the journey-persist write; global auth middleware built opt-in (Increment 17); credential store + refresh + member-binding pending |
| **AWS deploy** — CDK (ECS Fargate, RDS Aurora, ElastiCache, S3) | Phase 5 | ❌ |

**One-line status:** the framework is *demonstrable and governed end-to-end offline*, but the substance —
onboarding, real generation, write-back, persistence, and enforced gates — is still ahead of us.
