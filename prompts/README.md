# Prompt Library (reference content)

This directory is the **human-facing prompt library** — one Markdown prompt per persona/task
(`ba/user-stories.md`, `architect/adr-authoring.md`, `lead/pr-gate-review.md`, …). Each prompt
encodes the APEX golden rules and a Markdown-only output contract for a given SDLC task.

## What it is (and isn't)

- **Reference content, not runtime-loaded.** The platform's agents build their prompts in
  [`platform/backend/app/agents/prompts.py`](../platform/backend/app/agents/prompts.py), which is
  *adapted from* this library but does not read these files at runtime. Keeping the two in sync is a
  documentation discipline, not a code dependency.
- **A starting point for tuning.** When an agent's output needs adjusting, edit the corresponding
  prompt here first (it reads cleanly, reviews well), then port the change into `prompts.py`.

## Layout

```
prompts/<persona>/<task>.md   e.g. prompts/qa/test-cases.md
```

Personas mirror the platform's persona catalog (`developer`, `ba`, `qa`, `pm`, `lead`, `architect`,
`ciso`). See [`docs/personas.md`](../docs/personas.md) for the persona → phase → agent mapping.
