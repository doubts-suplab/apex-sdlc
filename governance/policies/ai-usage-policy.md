# APEX AI Usage Policy
**Version:** 1.0 | **Owner:** AI Review Board | **Effective:** 2025-Q3 | **Review cycle:** Quarterly

---

## 1. Purpose

This policy governs the use of AI coding assistants (Claude Code, GitHub Copilot) and AI automation pipelines within projects operating under the APEX framework. It protects the organisation from data leakage, model hallucinations entering production, intellectual property risk, and non-compliant AI-generated content.

---

## 2. Scope

Applies to all team members using AI tools on APEX-governed projects, including: developers, BAs, QA engineers, programme managers, agile coaches, and any automation pipelines running Claude or Copilot.

---

## 3. Permitted Uses

| Category | Permitted | Requires review |
|---|---|---|
| Code generation (new features) | ✅ | PR review gate |
| Test generation (unit, integration) | ✅ | Coverage gate (80%) |
| Code explanation / documentation | ✅ | None |
| Refactoring suggestions | ✅ | Tech lead sign-off |
| BA artefacts (user stories, AC) | ✅ | BA peer review |
| Sprint reporting (exec summaries) | ✅ | PM sign-off |
| Security vulnerability analysis | ✅ | Security guild review |
| Architecture decisions | ⚠️ | ARB approval required |
| Mainframe code modification | ❌ | See Mainframe Gate Policy |
| Production database queries | ❌ | DBA approval required |
| Customer PII processing | ❌ | DPO sign-off required |

---

## 4. Data Classification Rules

### 4.1 What MUST NOT be pasted into any AI tool

- Production database dumps or exports
- Customer names, email addresses, national IDs, financial data (PII/PCI)
- API keys, secrets, passwords, or AWS credentials
- Proprietary algorithms marked **CONFIDENTIAL** or **RESTRICTED**
- Unpublished financial results or M&A information
- Third-party source code covered by restrictive licences

### 4.2 What MAY be used with standard tools (Claude.ai / Copilot)

- Anonymised or synthetic data (real field names, fake values)
- Internal business logic that is not PII-adjacent
- Architecture diagrams and design documents (non-sensitive)
- Test data with no connection to real individuals

### 4.3 What requires the enterprise-grade Claude API (not consumer Claude.ai)

- Any code that touches customer records
- Automated pipelines processing sprint/Jira data
- Anything logging outputs to shared systems (Confluence, Slack)

> **Why:** Enterprise API data is not used for model training. Consumer Claude.ai inputs may be used for improvement unless opted out at the organisation level.

---

## 5. Code Review Gates

All AI-generated code **must** pass the following gates before merging:

1. **Automated PR review** — GitHub Actions `ai-pr-review.yml` runs on every PR
2. **Human reviewer** — at least one human must review AI-generated files, not just approve the auto-check
3. **Security scan** — `ai-pr-review.yml` OWASP check must show no HIGH findings
4. **Golden Rules check** — eeik_bootstrap rules enforced (no `@Autowired`, no `javax.*`, no `SELECT *`, etc.)
5. **Test coverage gate** — JaCoCo/Istanbul must report ≥80% line coverage on changed files

AI-generated commits must include the label `ai-assisted` (applied automatically by the PR workflow).

---

## 6. Hallucination Risk Controls

AI models can produce plausible-sounding but incorrect outputs. Mitigate as follows:

| Risk | Control |
|---|---|
| Invented API contracts | Always validate generated OpenAPI specs against running service |
| Wrong business rules in generated tests | BA must sign off on AC before tests go green |
| Security vulnerabilities in generated code | Security guild spot-check of `security-review-needed` labelled PRs |
| Outdated dependency versions | Dependabot + `mvn versions:display-dependency-updates` on merge |
| Invented architecture decisions | All AI-suggested ADRs go through ARB before adoption |

---

## 7. Intellectual Property

- **Ownership:** AI-generated code contributed to a company project is owned by the company, subject to the same IP assignment as human-authored code.
- **Copyright contamination:** If Copilot suggests a block >150 characters that appears verbatim in open-source code, reject it and rewrite manually. Use Copilot's "Show references" feature to check provenance.
- **Model provider terms:** Anthropic and GitHub Copilot terms permit enterprise customers to own their outputs. Verify before using any third-party AI tool not listed in this policy.

---

## 8. Audit and Logging

The APEX governance pipeline logs the following for every AI-assisted action:

| Event | Log destination | Retention |
|---|---|---|
| PR review AI output | GitHub Actions log + S3 audit bucket | 90 days |
| Claude API call (Jira bridge) | CloudWatch Logs | 30 days |
| PII scan result | S3 audit bucket (encrypted) | 1 year |
| ARB approval/rejection | Confluence ARB log page | Indefinite |
| Mainframe Gate status | governance/mainframe-gate-log.md | Indefinite |

---

## 9. Violations

| Severity | Example | Response |
|---|---|---|
| Low | Using consumer Claude.ai for internal docs | Reminder + policy re-training |
| Medium | Committing AI code without PR review | PR reverted, incident raised |
| High | Pasting customer PII into external AI tool | Security incident, DPO notified, disciplinary review |
| Critical | AI-generated code bypasses security gate and reaches production | P1 incident, root cause analysis, ARB review |

---

## 10. AI Review Board

The AI Review Board (ARB) meets fortnightly and is responsible for:

- Approving new AI tools for use on APEX projects
- Reviewing HIGH-severity violations and determining remediation
- Signing off on mainframe gate transitions (see Mainframe Gate Policy)
- Updating this policy quarterly

**Current ARB members:** Tech Lead, Security Guild Lead, BA Lead, Programme Manager, Enterprise Architect

---

## 11. Policy Review Schedule

| Quarter | Review focus |
|---|---|
| Q3 2025 | Initial release — establish baselines |
| Q4 2025 | Mainframe gate review (Week 17 target) |
| Q1 2026 | Velocity and quality KPI review; expand permitted uses if gates pass |
| Q2 2026 | Annual full review; update for new Claude/Copilot model versions |
