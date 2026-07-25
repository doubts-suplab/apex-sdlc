# Vendored eeik onboarding assets — provenance

These files are a **verbatim vendored copy** of onboarding data from
[`doubts-suplab/eeik-bootstrap`](https://github.com/doubts-suplab/eeik-bootstrap), so APEX can run the
onboarding front door standalone (in production APEX does not have the eeik repo on disk). They are **data,
not code** — eeik remains the single source of truth.

| Vendored file | eeik source | 
|---|---|
| `capability-matrix.yaml` | `generators/capability-selector/capability-matrix.yaml` |
| `questions/*.yaml` | `bootstrap/questions/*.yaml` |
| `examples/*.yaml` | `bootstrap/examples/*.yaml` |
| `manifest-schema.json` | `eeik/schemas/manifest.schema.json` (canonical, since eeik v1.4 — ADR-005) |

**Synced from eeik-bootstrap @ `b7bb2f6`.**

## Sync rule
When eeik changes the manifest schema, question sets, or capability matrix, re-copy these files and update
the SHA above (and re-check `app/onboarding/manifest.py`, which mirrors the schema as a Pydantic model).
This mirrors the convention already used for `docs/personas.md` ↔ `app/agents/catalog.py`.

## Live-engine option (preferred when eeik is installed)

As of eeik v1.4, eeik ships an installable engine with a stable Python SDK and an MCP server. When the
`eeik` package is available, APEX can consume the **real** engine instead of this vendored copy — via
[`app/onboarding/eeik_engine.py`](../eeik_engine.py):

- **SDK** (in-process): `import eeik` — `onboard_with_eeik(manifest, mode="sdk")`.
- **MCP** (over the protocol): spawns `eeik mcp` — `onboard_with_eeik(manifest, mode="mcp")`.

eeik then owns manifest validation (its canonical schema) and pack resolution; this vendored data remains
the **standalone-offline fallback** for when eeik is not on the host. See `app.demo.eeik_engine_demo`.

> Note: `app/onboarding/manifest.py` (the Pydantic model) can emit fields eeik's canonical schema rejects
> (e.g. a `modernization.source_technology` default) — `onboard_with_eeik` validates the manifest *as
> provided*, before building the model. Reconciling the model with the canonical schema is tracked work.
