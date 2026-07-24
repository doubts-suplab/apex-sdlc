# Vendored eeik onboarding assets — provenance

These files are a **verbatim vendored copy** of onboarding data from
[`doubts-suplab/eeik-bootstrap`](https://github.com/doubts-suplab/eeik-bootstrap), so APEX can run the
onboarding front door standalone (in production APEX does not have the eeik repo on disk). They are **data,
not code** — eeik remains the single source of truth.

| Vendored file | eeik source | 
|---|---|
| `capability-matrix.yaml` | `bootstrap/resolvers/capability-matrix.yaml` |
| `questions/*.yaml` | `bootstrap/questions/*.yaml` |
| `examples/*.yaml` | `bootstrap/examples/*.yaml` |
| `manifest-schema.json` | `bootstrap/schemas/manifest-schema.json` |

**Synced from eeik-bootstrap @ `b7bb2f6`.**

## Sync rule
When eeik changes the manifest schema, question sets, or capability matrix, re-copy these files and update
the SHA above (and re-check `app/onboarding/manifest.py`, which mirrors the schema as a Pydantic model).
This mirrors the convention already used for `docs/personas.md` ↔ `app/agents/catalog.py`.
