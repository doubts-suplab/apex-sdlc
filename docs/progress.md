# APEX Platform — Progress

An honest, increment-by-increment view of what is **built** vs **planned**. Newest first. This tracker
deliberately separates *structure* (the seams exist and are governed) from *substance* (real generation,
write-back, persistence, gates) so the [ROADMAP](../ROADMAP.md) and the code never drift apart.

Legend: ✅ done · 🚧 partial · ❌ not started

---

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
- ❌ **Not yet:** persisting `pii_events` rows (the model/table is still pending — findings are logged, not
  stored), the Comprehend NLP layer (names/addresses), and the **physical** retirement of the root
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
- ❌ **Not yet:** an Alembic baseline (the repo has **no** migrations — schema is via `metadata.create_all`;
  a full initial migration is a follow-on), S3 storage, and auth/RBAC on the new endpoints.
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
- ❌ **Not yet:** full compilable repo-tree emission + actually creating a GitHub repo (the LLM-driven eeik
  `repository-generator` path); persisting the onboarded project to the DB registry.

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
- 🚧 ORM models cover `organisation`, `project`, `integration`, `phase`, **`artifact`, `agent_run`** —
  still **missing** `team`, `member`, `artifact_version`, `audit_log`, `pii_event`, `policy_violation`.
- ❌ No Alembic migrations yet (`versions/` empty; schema via `metadata.create_all`). 🚧 PII-guard
  middleware now scrubs/scans agent LLM I/O (Increment 7); 🚧 JWT + persona RBAC guards the persist write
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
| **Live integrations** — GitHub/Jira/Confluence live data + background refresh | Phase 2 | 🚧 clients exist, not wired to refresh/agents |
| **Agent write-back** — create Jira epics/stories, post GitHub PR reviews, publish Confluence | Phase 3 | ❌ agents don't call integrations |
| **Dev repo bootstrap** — scaffold the actual service (eeik `repository-generator`) | Phase 0 / 3 | ❌ |
| **Architect target-architecture** — reason over requirements + existing system → target-state ADR/C4 | Phase 4 | ❌ (templated ADR only today) |
| **Artifact persistence** — artifacts + agent runs + gates in DB, with version lineage | Phase 4 | 🚧 DB persistence + version lineage built (SQLite-verified); S3 + Alembic baseline pending |
| **Phase-gate engine** — enforce the spec-driven spine's phase transitions | Phase 5 | 🚧 pure engine + API + UI built offline; DB persistence + approval store pending |
| **PII guard on agent I/O** — regex scrub outgoing / scan+log incoming on every LLM call | Phase 5 | 🚧 middleware built + wired (Increment 7); `pii_events` persistence + Comprehend NLP layer pending |
| **Governance persistence** — audit_log, pii_events, policy_violations tables + CISO view + ARB | Phase 5 | ❌ |
| **Auth & RBAC** — JWT, persona-scoped access | Phase 5 | 🚧 HS256 JWT + `require_persona` built (Increment 8), guarding the journey-persist write; global middleware + credential store + refresh pending |
| **AWS deploy** — CDK (ECS Fargate, RDS Aurora, ElastiCache, S3) | Phase 5 | ❌ |

**One-line status:** the framework is *demonstrable and governed end-to-end offline*, but the substance —
onboarding, real generation, write-back, persistence, and enforced gates — is still ahead of us.
