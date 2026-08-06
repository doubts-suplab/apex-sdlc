# CLAUDE.md Template Library (reference content)

Per-project-type `CLAUDE.md` seed templates (`spring-boot/`, `angular/`, `shared-lib/`, `mainframe/`).
Each is a ready-to-adapt project brief encoding the APEX golden rules and stack-specific standards for
that project type.

## What it is (and isn't)

- **Reference content, not runtime-loaded.** The Architecture agent produces a project `CLAUDE.md` as a
  governed artifact; these templates are the human-authored reference it is modelled on, not a file the
  platform reads at runtime. Onboarding's own scaffolder
  ([`platform/backend/app/onboarding/`](../platform/backend/app/onboarding/)) emits a tailored
  `CLAUDE.md` from the resolved manifest.
- **Consumed by convention, not code.** The `ai-pr-review` workflow and `platform/CLAUDE.md` link here as
  the canonical standards reference for each stack.

## Layout

```
claude-templates/<project-type>/CLAUDE.md   e.g. claude-templates/spring-boot/CLAUDE.md
```
