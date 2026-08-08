# Contributing to APEX SDLC

Thanks for your interest in APEX. This guide explains how to get a working offline setup, the
conventions the codebase follows, and what a good contribution looks like.

APEX is **onboarding-first, spec-driven, and governed** — every AI action runs on the generic
[agent-harness](https://github.com/doubts-suplab/agent-harness) and is auditable. Two disciplines run
through everything below: **the offline path must stay reproducible** (no credentials or infra to run the
demos and tests), and **the committed `examples/` are byte-identical fixtures** — a change that alters them
must be intentional and reviewed.

---

## Quick start (offline, no credentials)

Everything in the reference journey runs with the deterministic stub provider — no Postgres, Redis, S3, or
API keys.

```bash
cd platform/backend
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'

# Regenerate the reference journey (writes examples/reference-project/artifacts/**)
LLM_PROVIDER=stub python -m app.demo.reference_journey

# Run the governance test suite
pytest --noconftest tests/agents/
```

If you have [`make`](https://www.gnu.org/software/make/) available, `make help` (from the repo root) lists
every offline demo and test target, and `make smoke` runs the one-command smoke test (reference journey +
gate report + a test subset, asserting `examples/` stays byte-identical).

---

## Project layout

The runnable platform lives under [`platform/`](platform/); the root also holds framework docs
([`docs/`](docs/)), committed fixtures ([`examples/`](examples/)), and two **reference libraries**
([`prompts/`](prompts/) and [`claude-templates/`](claude-templates/)) that are human-authored, not
runtime-loaded. See [`platform/CLAUDE.md`](platform/CLAUDE.md) and
[`platform/backend/CLAUDE.md`](platform/backend/CLAUDE.md) for the architecture and the backend
non-negotiables, and [`docs/progress.md`](docs/progress.md) for an honest built-vs-planned view.

---

## Development workflow

1. **Branch** off `main`.
2. **Make one coherent change per PR.** APEX is built increment-by-increment (see
   [`docs/progress.md`](docs/progress.md)); mirror that — small, complete, self-describing changes.
3. **Keep the offline path green and deterministic:**
   - `pytest` passes (`cd platform/backend && pytest`).
   - `ruff check app tests` and `ruff format --check app tests` are clean.
   - `mypy app` is clean (the backend is `strict`).
   - If your change is *not* meant to alter the committed fixtures, `examples/` must stay
     **byte-identical** after re-running the demos. `git status` should show no `examples/` churn.
     `make smoke` checks this for you.
4. **Frontend changes** (`platform/frontend/`): `npm run type-check` and `npm run build` must pass; state
   goes through TanStack Query hooks and Zod schemas that mirror the backend.
5. **Update the docs in the same PR.** The persona/phase catalog is a **single source of truth**
   ([`docs/personas.md`](docs/personas.md), mirrored by
   [`platform/backend/app/agents/catalog.py`](platform/backend/app/agents/catalog.py)) — if you touch one,
   update the other, and reflect the increment in [`docs/progress.md`](docs/progress.md).

---

## Coding conventions

**Backend (Python 3.11+, FastAPI, SQLAlchemy 2.x async).** The full list is in
[`platform/backend/CLAUDE.md`](platform/backend/CLAUDE.md); the load-bearing ones:

- `async/await` throughout — no synchronous DB/HTTP/`time.sleep` in async paths.
- Pydantic v2 API (`model_validate`, `model_dump`); structlog only (no `print`).
- No `SELECT *`, no raw SQL string-formatting, no ORM lazy loading (`lazy="raise"` +
  `selectinload`/`joinedload`).
- **PII guard on all agent I/O** and **one `audit_log` entry per agent run** — these are non-negotiable
  governance rules, not conventions.
- Agents **propose** a `Decision`; the harness decides auto-enforcement. Never set `auto_enforced` in an
  agent, and never bypass the confidence gate. SUGGEST-authority phases can never auto-enforce (gate rule
  **G-5**).

**Frontend (Next.js 14 App Router, TypeScript strict).** shadcn/ui components only; no `any`; Zod schemas
mirror backend Pydantic models; all API calls go through TanStack Query hooks.

---

## Tests

- pytest + pytest-asyncio (`asyncio_mode = "auto"`); API tests use `httpx.AsyncClient` against the app —
  no real network. DB tests run against in-memory SQLite (`aiosqlite`) offline; Postgres in production.
- New behavior needs a test. Governance behavior (authority ladder, gates, PII, audit) especially — those
  are the guarantees APEX makes.

---

## Commit and PR conventions

- **Conventional-commit style** subjects: `feat(agents): …`, `fix(webhooks): …`, `docs(roadmap): …`,
  `refactor(repo): …`.
- Reference the ROADMAP phase / progress increment where relevant.
- Fill out the PR template checklist. A green offline path (tests, lint, byte-identical `examples/`) is the
  baseline for review.

---

## Reporting bugs and requesting features

Use the issue templates:
[bug report](.github/ISSUE_TEMPLATE/bug_report.md) ·
[feature request](.github/ISSUE_TEMPLATE/feature_request.md). For anything security-sensitive, please do
**not** open a public issue — see the security note in the templates.

---

## Third-party references

APEX consumes two external projects — [agent-harness](https://github.com/doubts-suplab/agent-harness) (the
governed runtime) and eeik (the onboarding engine). APEX does not vendor or re-license them; it depends on
the harness as a package and consumes eeik via its SDK/MCP when installed. Contributions should preserve
that boundary — APEX supplies *agents* and *infrastructure adapters*, not a re-implementation of the
runtime.
