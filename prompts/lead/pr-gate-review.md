# Prompt: PR Gate & Definition-of-Done Review (Tech Lead)
# APEX Prompt Library · Category: Lead · Tool: Claude Code CLI + GitHub
# Maps to: Development / CI-CD phases · Agent: PRReviewerAgent / ReleaseEngineerAgent (harness authority: ALERT / RATE_LIMIT)

---

## Definition-of-Done Gate Check

```
You are a Tech Lead performing a pre-merge Definition-of-Done review. Assess this PR against the DoD
and return a GO / NO-GO with specific blockers.

Definition of Done:
- [ ] Acceptance criteria from the linked story are all met
- [ ] Unit + integration tests added; coverage does not drop below 80% line / 70% branch
- [ ] No golden-rule violations (constructor injection, no SELECT *, parameterised SQL, SLF4J/structlog,
      no hardcoded secrets, jakarta not javax on Boot 3.x)
- [ ] No PII in logs; no secrets in code
- [ ] OpenAPI / docs updated if the API surface changed
- [ ] Migration script + rollback present if the schema changed

For each unmet item, cite the file:line and the specific fix. End with:
Decision: GO / NO-GO / CONDITIONAL GO (list conditions)

PR diff + linked story:
[PASTE DIFF AND STORY]
```

---

## Tech-Debt Triage

```
Triage the tech-debt items below for the next sprint. For each item assign:
- Priority (P0 blocking / P1 this quarter / P2 backlog)
- Effort (raw hours → Human Days = Σ hours ÷ 6.4)
- Risk if deferred (one sentence)
- Recommended target sprint

Output as a markdown table sorted by priority, then a one-paragraph recommendation on what to pull
into the next sprint given a [N]-point capacity.

Tech-debt register:
[PASTE]
```

---

## Merge-Readiness Summary for the Squad

```
Summarise the state of the open PRs below for a stand-up. For each PR: title, author, age, blocking
review comments outstanding, CI status, and a one-line "what's needed to merge". Flag any PR older
than 3 days or with an approval that a new push would invalidate.

Open PRs:
[PASTE PR LIST / EXPORT]
```
