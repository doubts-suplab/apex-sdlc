# DevOps Flow — Proposed Plan (dry run)

**Intent:** open a PR and notify the team
**Status:** held for human review — not executed
**Planned calls:** 2

| # | Tool | Arguments |
|---|------|-----------|
| 1 | `github.open_pull_request` | `{"base": "main", "head": "feature/refund-retry-fix", "repo": "org/UNSET-REPO", "title": "feat: Refund retry fix"}` |
| 2 | `slack.post_message` | `{"channel": "#UNSET", "text": "Shipped: Refund retry fix."}` |
