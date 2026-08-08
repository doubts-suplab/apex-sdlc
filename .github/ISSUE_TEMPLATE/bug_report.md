---
name: Bug report
about: Report something that behaves incorrectly in APEX
title: "bug: "
labels: bug
assignees: ''
---

<!--
Security-sensitive issue (a way to bypass the confidence gate, leak PII, forge an audit entry,
or exfiltrate credentials)? Please do NOT file it here. Report it privately to the maintainers first.
-->

## What happened

A clear, concise description of the bug.

## Expected behavior

What you expected to happen instead.

## Reproduction

Steps to reproduce — prefer the **offline path** (stub provider, no credentials) where possible:

```bash
cd platform/backend
LLM_PROVIDER=stub python -m app.demo.reference_journey
# ...
```

## Area

- [ ] Backend (FastAPI / agents / gates / persistence)
- [ ] Frontend (Next.js portal)
- [ ] Onboarding (eeik bridge)
- [ ] Integrations / webhooks
- [ ] Governance (audit / PII / policy / authority ladder)
- [ ] Docs / examples
- [ ] Other

## Environment

- APEX commit / branch:
- Python version:
- `LLM_PROVIDER` (stub / anthropic / …):
- OS:

## Did the committed fixtures change?

APEX's `examples/` are byte-identical fixtures. If running a demo changed them unexpectedly, paste the
relevant `git status` / `git diff --stat examples/` output — that is often the clearest signal.

## Logs / output

<details>
<summary>Relevant logs</summary>

```
paste here
```

</details>
