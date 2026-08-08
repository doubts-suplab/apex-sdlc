<!--
Thanks for contributing to APEX! Keep changes small and complete (one coherent increment per PR).
See CONTRIBUTING.md for the full workflow.
-->

## What this changes

A concise description of the change and why.

## Related

- Roadmap phase / progress increment:
- Closes #

## Type of change

- [ ] Feature
- [ ] Fix
- [ ] Refactor / consolidation
- [ ] Docs
- [ ] Tests / tooling

## Checklist

**Offline path stays green and deterministic:**

- [ ] `cd platform/backend && pytest` passes
- [ ] `ruff check app tests` and `ruff format --check app tests` are clean
- [ ] `mypy app` is clean
- [ ] `examples/` is **byte-identical** after re-running the demos — or the fixture change is intentional
      and called out below (`make smoke` checks this)

**Frontend (if touched):**

- [ ] `npm run type-check` passes
- [ ] `npm run build` passes

**Governance & docs:**

- [ ] No confidence-gate bypass; agents only *propose* (SUGGEST phases never auto-enforce — G-5)
- [ ] PII guard + one `audit_log` entry per agent run preserved (if agent I/O is touched)
- [ ] Persona/phase catalog kept in sync (`docs/personas.md` ↔ `app/agents/catalog.py`) if touched
- [ ] `docs/progress.md` updated with this increment (if it changes built-vs-planned status)

## Intentional fixture changes

If this PR changes anything under `examples/`, explain why here (otherwise write "none").
