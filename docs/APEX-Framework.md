# APEX Framework
## AI-Powered Engineering eXperience — Enterprise SDLC Augmentation Plan
### Stack: Angular · Java · Spring Boot · Mainframe | Tools: Claude Code · GitHub Copilot

---

> **Platform Evolution — June 2026**
> APEX has grown beyond CLI/desktop augmentation into a full SDLC operating platform. The framework principles, governance model, and adoption strategy described in this document remain valid and are now enforced by the APEX Platform itself.
>
> **What's new:**
> - **`platform/`** — FastAPI backend + Next.js 14 frontend + PostgreSQL + Redis + Celery running as cloud-native containers (AWS ECS Fargate locally via Docker Compose)
> - **Live integrations** — GitHub, Jira, Rally, and Confluence are wired as live data sources (Celery background refresh), not just webhook triggers
> - **Flexible LLM layer** — Agents run on Anthropic, Ollama (local), Groq, HuggingFace, or a deterministic `stub` (offline demo) — switchable via `LLM_PROVIDER` env var with no code changes
> - **Per-phase AI agents on a governed runtime** — an agent for each of the seven SDLC phases generates artifacts, but agent *execution* is delegated to the generic [**agent-harness**](https://github.com/doubts-suplab/agent-harness): APEX does not re-implement the confidence gate, the tool registry, audit, human-review routing, or safe-failure defaults. Agents *propose*; the harness *governs*.
> - **All seven personas served** — Developer, BA, QA, PM, Tech Lead, Architect, and CISO each own or consume a phase, with a dedicated agent, prompt set, and artifacts. See [`docs/personas.md`](personas.md).
> - **A runnable reference journey** — [`examples/reference-project/`](../examples/reference-project/README.md) walks one project through all seven phases offline, producing 17 real artifacts, as a worked demonstration of the framework.
> - **Onboarding-first &amp; spec-driven** — the target shape is: *onboard* a project via eeik (scaffold repo + `CLAUDE.md` + capability packs), then run a governed **spec-driven spine** where each phase's approved artifact gates the next. See the [Product Vision](../ROADMAP.md#product-vision--onboarding-first-spec-driven) and the honest [build status](progress.md).
> - **`portal-prototype/`** — the original static portal is retained as a reference; the live portal is `platform/frontend/`
>
> See [`ROADMAP.md`](../ROADMAP.md) for the full 5-phase build plan, [`docs/personas.md`](personas.md) for the persona catalog, and [`platform/CLAUDE.md`](../platform/CLAUDE.md) for the platform architecture.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Framework Architecture](#2-framework-architecture)
3. [What to Build vs What to Integrate](#3-what-to-build-vs-what-to-integrate)
4. [Step-by-Step Implementation Plan](#4-step-by-step-implementation-plan)
5. [Rollout Strategy](#5-rollout-strategy)
6. [Team Structure & Skills Required](#6-team-structure--skills-required)
7. [Governance Integration](#7-governance-integration)
8. [Adoption Guide](#8-adoption-guide)
9. [Success Metrics](#9-success-metrics)
10. [Appendix: CLAUDE.md Template & Prompt Library](#10-appendix)

---

## 1. Executive Summary

APEX is a non-intrusive AI augmentation layer that sits alongside your existing SDLC without replacing any tooling or ceremony. It routes the right AI capability to the right persona at the right stage of delivery — developers get Claude Code and Copilot in their IDEs, BAs and PMs get prompt-powered Confluence and Jira automation, testers get AI-generated test suites, and leadership gets AI-synthesized status reports.

**Core principles:**
- Zero new tools for non-engineering personas
- AI generates drafts; humans approve and commit
- Every AI action is logged, audited, and governed
- Adopt incrementally — one team, one sprint, one phase at a time

**Expected outcomes at 6 months:**
- 30–40% reduction in PR cycle time
- 50%+ reduction in boilerplate code authoring time
- 60% reduction in manual test case writing effort
- Near-zero undocumented COBOL programs (legacy modernisation)
- Consistent story quality scores across all squads

---

## 2. Framework Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        APEX FRAMEWORK LAYERS                        │
├─────────────────────────────────────────────────────────────────────┤
│  PERSONA LAYER                                                      │
│  Dev (IDE)  │  BA/PM (Claude.ai)  │  Tester (CLI)  │  Stakeholder  │
├─────────────────────────────────────────────────────────────────────┤
│  AI ORCHESTRATION LAYER                                             │
│  Claude Code CLI  │  Copilot API  │  Claude API (Haiku/Sonnet)     │
├─────────────────────────────────────────────────────────────────────┤
│  INTEGRATION LAYER                                                  │
│  Jira  │  Confluence  │  GitHub  │  SonarQube  │  Slack/Teams      │
├─────────────────────────────────────────────────────────────────────┤
│  GOVERNANCE LAYER                                                   │
│  Audit Log  │  Policy Engine  │  PII Guard  │  Approval Gates      │
├─────────────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                         │
│  CLAUDE.md files  │  Prompt Library  │  Metrics Store              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 Key Design Decisions

**Claude Code vs GitHub Copilot — complementary, not competing**

| Capability | Claude Code | GitHub Copilot |
|---|---|---|
| Multi-file agentic edits | ✅ Primary | ❌ |
| Inline IDE autocomplete | Limited | ✅ Primary |
| Terminal / CLI workflow | ✅ Native | ❌ |
| PR description generation | ✅ | ✅ |
| COBOL / legacy analysis | ✅ Superior | Limited |
| M365 integration | ❌ | ✅ (Copilot M365) |
| Cost model | Usage-based API | Per-seat licence |

**Rule of thumb:** Copilot for keystrokes saved per minute; Claude Code for decisions made per hour.

---

## 3. What to Build vs What to Integrate

### 3.1 Integrate (Off-the-shelf — no custom build needed)

| Tool | Purpose | Persona |
|---|---|---|
| Claude Code CLI | Agentic coding, refactoring, test gen | Developers, Testers |
| GitHub Copilot | IDE inline completion | Developers, Testers |
| Claude.ai Desktop / Web | Chat interface for non-devs | BA, PM, Coach, Stakeholder |
| GitHub Copilot M365 | Word, Excel, Outlook AI | PM, Stakeholder |
| GitHub Copilot for PR | PR description, review suggestions | Developers |
| Anthropic Claude API | Backend automation pipelines | Platform team |

### 3.2 Build (Custom — your differentiator)

#### A. CLAUDE.md Templates (Low effort, High ROI)
Per-repo context files that tell Claude Code your architecture, conventions, and constraints. One file per repo type:
- `CLAUDE.md` for Spring Boot microservices
- `CLAUDE.md` for Angular SPA
- `CLAUDE.md` for Mainframe COBOL batch
- `CLAUDE.md` for shared libraries

**What goes in a CLAUDE.md:**
```markdown
# Project Context
- Stack: Spring Boot 3.x, Java 21, PostgreSQL, Kafka
- Architecture: Hexagonal / Clean Architecture
- Naming: camelCase services, PascalCase DTOs
- Test framework: JUnit 5 + Mockito + Testcontainers
- Forbidden: no @Autowired on fields, no lombok @Data on entities
- API style: REST, OpenAPI 3.0, versioned under /api/v{n}/
- Package structure: .domain / .application / .infrastructure / .web
```

#### B. Prompt Library Portal (Medium effort)
A shared internal web page / Confluence space containing curated prompts per persona and ceremony. Developers paste once; non-devs click-to-copy.

**Prompt categories to build:**
- Sprint Planning: story refinement, estimation, dependency mapping
- Development: refactor patterns, migration stubs, DTO generation
- Testing: AC-to-test-case, API collection generation, edge case generator
- Review: PR summary, security checklist, OWASP scan prompt
- Reporting: sprint summary, exec dashboard, release notes
- COBOL: program explainer, JCL decoder, migration readiness assessment

#### C. Jira → Claude Automation Bridge (Medium effort)
A lightweight service (Python/Node) that:
1. Triggers on Jira webhook (sprint complete, ticket status change)
2. Calls Claude API with relevant Jira data
3. Writes output back to Confluence or creates a Jira comment

**Automations to build (priority order):**
1. Sprint End → Draft retrospective notes in Confluence
2. New Epic → Draft BRD template pre-populated with description
3. Bug closed → Auto-generate regression test stub in repo
4. Story "In Review" → Summarise PR diff in plain English for BA

#### D. CI/CD AI Gates (Medium-High effort)
GitHub Actions workflows that invoke Claude Code or Claude API at key pipeline stages:

```yaml
# .github/workflows/ai-review.yml
on: [pull_request]
jobs:
  ai-review:
    steps:
      - name: Claude Security Review
        run: claude --print "Review this diff for OWASP Top 10 issues" --diff
      - name: Generate PR Summary
        run: claude --print "Write a plain-English PR description"
      - name: Check test coverage delta
        run: claude --print "Identify untested methods in the diff"
```

**Gates to implement:**
- PR opened → AI security scan (non-blocking, advisory)
- PR opened → Auto-generate description if empty
- Merge to main → Update OpenAPI spec from code changes
- Release tag → Generate release notes from commit history

#### E. Governance Dashboard (Medium effort)
A web dashboard (React or simple HTML/JS) that shows:
- AI usage by team, persona, and week
- Prompt audit log (who asked what, when)
- Policy violations flagged
- Code acceptance rate (AI suggestions committed vs discarded)
- PII detection alerts

#### F. APEX Developer Portal (Low-Medium effort)
Single-page internal site that serves as the APEX home base:
- Getting started guide per persona (interactive)
- CLAUDE.md builder (form → generates context file)
- Prompt library browser
- Framework status and metrics
- Governance policy documentation

---

## 4. Step-by-Step Implementation Plan

### Phase 0 — Foundation (Weeks 1–2)

**Goal:** Install tools, establish baseline, no automation yet.

- [ ] Procure Claude Code licences (team plan) and GitHub Copilot Business seats
- [ ] Install Claude Code CLI on dev machines; verify `claude --version` in all IDEs
- [ ] Enable GitHub Copilot in IntelliJ IDEA and VS Code
- [ ] Draft AI Usage Policy v1 (see Section 7)
- [ ] Create `#ai-sdlc` Slack/Teams channel for sharing tips and issues
- [ ] Identify pilot squad (1 squad, ideally cross-functional)
- [ ] Baseline metrics: PR cycle time, bug escape rate, story points velocity

### Phase 1 — Developer Pilot (Weeks 3–6)

**Goal:** Prove value with developers first. Non-devs observe.

- [ ] Write `CLAUDE.md` for the pilot squad's primary repo (Spring Boot or Angular)
- [ ] Run a 2-hour Claude Code workshop: refactoring, test gen, PR review
- [ ] Run a 1-hour Copilot workshop: Angular component gen, Spring boilerplate
- [ ] Define daily check-in: "What did AI help you with today? What didn't work?"
- [ ] Collect Week 2 metrics vs baseline
- [ ] Publish `CLAUDE.md` templates to inner-source repo for other squads to adapt

### Phase 2 — BA, PM & QA Onboarding (Weeks 7–10)

**Goal:** Extend AI to non-dev personas with near-zero friction.

- [ ] Set up Claude.ai Desktop for BAs and PMs (Team plan)
- [ ] Build Prompt Library v1 in Confluence (10–15 prompts per persona)
- [ ] Run per-persona 90-min workshops:
  - BA: Story generation, gap analysis, BRD drafting
  - PM: Sprint report generation, risk summarisation
  - QA: AC-to-test-case, API test generation
  - Agile Coach: Retro synthesis, velocity report
- [ ] Deploy Jira → Claude automation #1 (sprint end → Confluence retro draft)
- [ ] Collect feedback, iterate prompt library

### Phase 3 — CI/CD & Automation (Weeks 11–14)

**Goal:** Bake AI into the pipeline so it's invisible but always working.

- [ ] Deploy AI PR review GitHub Action (security scan + description)
- [ ] Deploy release notes automation (tag → Claude → GitHub Release)
- [ ] Deploy OpenAPI spec auto-update on merge
- [ ] Enable Copilot for PR in GitHub settings
- [ ] Connect Jira automation bridge for 3 key triggers
- [ ] Set up APEX Governance Dashboard (basic version: log viewer + metrics)

### Phase 4 — Scale & Govern (Weeks 15–20)

**Goal:** All squads live; governance active; metrics proving ROI.

- [ ] Roll out to remaining squads with adapted `CLAUDE.md` per repo
- [ ] Launch APEX Developer Portal internally
- [ ] Activate PII Guard in governance layer
- [ ] Establish AI Review Board cadence (monthly)
- [ ] Publish APEX metrics to leadership dashboard
- [ ] Begin Mainframe modernisation track: COBOL analysis pipeline
- [ ] Retrospective: tune adoption, retire what isn't working

---

## 5. Rollout Strategy

### 5.1 Rollout Model: Concentric Rings

```
Ring 1 (Wk 1–6):   Pilot Squad — Devs only
Ring 2 (Wk 7–10):  Pilot Squad — Full cross-functional (BA, QA, PM)
Ring 3 (Wk 11–14): 2–3 additional squads — Devs + CI/CD automation
Ring 4 (Wk 15–20): All squads — Full APEX live
```

### 5.2 Change Management Approach

**Fear to address proactively:**

| Fear | Response |
|---|---|
| "AI will replace me" | Frame as: AI removes drudge work; you focus on higher-order thinking |
| "IP / code leaking to Anthropic" | Claude Code (API mode) does not train on your data; show the data policy |
| "AI generates wrong code" | Human reviews all AI output before commit; AI is a junior pair programmer |
| "Too much to learn" | Each persona gets exactly 3 prompts to start with. That's it. |

**Communication plan:**
- Week 0: Leadership briefing (30 min) — why, what, how measured
- Week 1: All-hands announcement — "AI tools pilot, not mandatory yet"
- Week 3: Pilot squad kickoff — hands-on, no slides
- Week 7: Demo day — pilot squad shows what worked
- Week 15: Org-wide launch — metrics-backed, wins highlighted

### 5.3 Non-Intrusive Design Rules

1. **AI never commits code** — it only suggests. Humans always have final control.
2. **AI never sends to Jira/Confluence automatically** — automations write drafts, humans publish.
3. **Opt-in initially** — no forced adoption in Phase 1 or 2. Mandate only in Phase 4 for CI/CD gates.
4. **Graceful degradation** — if Claude API is down, the pipeline continues; AI step skips with a warning.
5. **No prompt logging to external systems** — all audit logs stay in your infrastructure.

---

## 6. Team Structure & Skills Required

### 6.1 Core APEX Team (4–5 people, 6-month build)

**Role 1: AI Platform Engineer (1 FTE)**
- Skills: Python, REST APIs, Anthropic Claude API, GitHub Actions, Webhooks
- Builds: Jira automation bridge, CI/CD AI gates, Claude API integrations
- Owns: Governance log pipeline, PII guard implementation

**Role 2: DevOps / Platform SRE (1 FTE or 0.5 FTE)**
- Skills: GitHub Actions, Docker, AWS (Lambda, SQS), IaC (CDK or Terraform)
- Builds: CI/CD workflows, APEX infrastructure, secrets management
- Owns: Reliability of all automation pipelines

**Role 3: Full-Stack Developer (1 FTE)**
- Skills: React or Vue, Node/Python, REST, basic data viz
- Builds: APEX Developer Portal, Governance Dashboard
- Owns: Internal tooling front-end

**Role 4: AI/Prompt Engineer + Change Lead (1 FTE)**
- Skills: Prompt engineering, technical writing, workshop facilitation, LLM evaluation
- Builds: Prompt library, CLAUDE.md templates, persona workshops
- Owns: Adoption metrics, feedback loop, prompt tuning

**Role 5: Security / Compliance Engineer (0.5 FTE)**
- Skills: AppSec, data governance, audit logging, GDPR/SOC2 awareness
- Reviews: AI Usage Policy, PII guard rules, audit log design
- Owns: Governance policy, AI Review Board secretariat

### 6.2 Extended Stakeholders (Part-time contributors)

- **Each Squad's Tech Lead** — Customises `CLAUDE.md` for their repo
- **Scrum Masters** — Integrate prompt library into ceremonies
- **Enterprise Architect (you)** — Framework governance, architecture guardrails, AI strategy
- **CISO / Security team** — Sign off on AI Usage Policy

### 6.3 Engagement Model

```
APEX Core Team (full-time)
    └── Squad AI Champions (one per squad, ~10% time)
            └── Persona leads (BA lead, QA lead, etc. — use the tools, share tips)
```

---

## 7. Governance Integration

### 7.1 AI Usage Policy (v1 Outline)

**Permitted uses:**
- Code generation, completion, and refactoring with human review
- Test case generation with human validation
- Documentation drafting with human approval
- Requirements and report drafting (non-binding until human approved)
- Summarisation of internal project data

**Prohibited uses:**
- Committing AI-generated code without human review
- Sending customer PII or production data to AI APIs
- Using AI output as the sole basis for architecture decisions
- Generating content that misrepresents AI as human-authored in external comms

**Licence considerations:**
- Claude Code: Output is not subject to Anthropic copyright claims (verify current ToS)
- GitHub Copilot: Copilot Business has IP indemnification — ensure Business tier is used

### 7.2 Governance Architecture

```
┌──────────────────────────────────────────────────────┐
│                  GOVERNANCE LAYER                     │
├──────────────────────────────────────────────────────┤
│  Policy Engine                                       │
│  - Allowlist of approved Claude models               │
│  - Blocklist of prompt patterns (e.g. "ignore rules")│
│  - Mandatory human-in-loop gate for production code  │
├──────────────────────────────────────────────────────┤
│  Audit Logger                                        │
│  - Every API call: timestamp, user, prompt hash,     │
│    model, token count, output accepted/rejected      │
│  - Stored in: your AWS S3 / internal SIEM            │
│  - Retention: 90 days minimum                        │
├──────────────────────────────────────────────────────┤
│  PII Guard                                           │
│  - Pre-prompt scanner: blocks SSN, PAN, account no. │
│  - Uses AWS Comprehend or regex + ML classifier      │
│  - Alert on violation; block request if critical     │
├──────────────────────────────────────────────────────┤
│  Approval Gates                                      │
│  - AI-generated PRs flagged with label "ai-assisted" │
│  - Mandatory 2-reviewer rule for AI-assisted PRs     │
│  - Architecture changes require EA sign-off          │
├──────────────────────────────────────────────────────┤
│  AI Review Board                                     │
│  - Monthly cadence                                   │
│  - Members: EA, CISO, Dev Lead, BA Lead, PM          │
│  - Reviews: usage metrics, policy violations,        │
│    model updates, new use-case requests              │
└──────────────────────────────────────────────────────┘
```

### 7.3 Governance Metrics to Track

| Metric | Target | Measured by |
|---|---|---|
| AI-assisted PR acceptance rate | > 70% | GitHub labels + merge data |
| Policy violations per month | < 5 | Audit log |
| PII detection blocks | 0 undetected leaks | PII guard alert log |
| AI usage coverage | > 80% of devs weekly | Claude Code telemetry |
| Human override rate | Tracked (no target) | PR review data |
| Model version currency | Within 1 major version | APEX config registry |

### 7.4 Integrating Governance into Existing Processes

**Sprint ceremonies:**
- Sprint planning: AI-generated stories marked `[AI-Draft]` until BA approves
- Sprint review: AI sprint summary presented, PM confirms before stakeholder send
- Retro: AI-synthesised retro notes are a starting point, coach facilitates discussion

**Change management:**
- All CLAUDE.md changes go through PR review by Tech Lead
- Prompt library changes reviewed by AI Platform Engineer before publish
- New automation triggers require AI Review Board approval

---

## 8. Adoption Guide

### 8.1 Day 1 Quick-Starts by Persona

**Developer (Day 1 — 20 minutes)**
1. Install: `npm install -g @anthropic-ai/claude-code`
2. Open your primary repo in terminal: `cd your-repo && claude`
3. First prompt: `"Explain the architecture of this codebase in 3 paragraphs"`
4. Second prompt: `"Generate JUnit 5 tests for the UserService class"`
5. Install Copilot extension in IntelliJ/VS Code; sign in with GitHub account
6. Done. Use it every day; share what works in `#ai-sdlc`

**Business Analyst (Day 1 — 10 minutes)**
1. Open Claude.ai Desktop (or claude.ai in browser)
2. Use this starter prompt: _"You are a BA on a Java/Angular enterprise project. I will paste meeting notes. Convert them into Jira user stories with acceptance criteria in Gherkin format."_
3. Paste your last meeting notes. Review output.
4. Bookmark the Prompt Library page (link)

**Tester / QA (Day 1 — 20 minutes)**
1. Install Claude Code CLI (same as dev)
2. Navigate to a feature branch: `cd feature-branch && claude`
3. First prompt: `"Read the UserController and generate a Postman collection for all endpoints"`
4. Second prompt: `"Given these acceptance criteria: [paste AC], write Cypress test cases"`

**Agile Coach / Scrum Master (Day 1 — 10 minutes)**
1. Open Claude.ai Desktop
2. Starter prompt: _"I will paste Jira sprint data. Synthesise a retrospective: what went well, what didn't, action items. Format as Confluence wiki markup."_
3. Export your sprint from Jira; paste into Claude

**Program Manager (Day 1 — 10 minutes)**
1. Open Claude.ai Desktop or Copilot in Word
2. Starter prompt: _"Here is a Jira sprint export. Write a 3-paragraph executive status update: progress, risks, and next sprint priorities. Plain English, no jargon."_

### 8.2 CLAUDE.md Quick-Builder

Copy this template into the root of each repo and fill in the blanks:

```markdown
# [Project Name] — Claude Code Context

## Architecture
- Pattern: [Hexagonal / Layered / MVC]
- Framework: [Spring Boot 3.x / Angular 17+]
- Java version: [21]
- Build: [Maven / Gradle]

## Conventions
- Naming: [camelCase services, PascalCase DTOs]
- Package structure: [domain / application / infrastructure / web]
- Test framework: [JUnit 5, Mockito, Testcontainers]

## Constraints
- Do NOT use: [@Autowired on fields, raw SQL, Lombok @Data on entities]
- Always do: [Add OpenAPI @Operation annotations to controllers]
- Security: [Spring Security, OAuth2 / Keycloak, no hardcoded credentials]

## Mainframe Integration (if applicable)
- Integration: [MQ / REST gateway / CICS]
- COBOL programs involved: [list key programs]
- Known quirks: [describe gotchas]

## What Claude should focus on
- Prefer [reactive / imperative] style
- PRs should include [test + javadoc + migration script if schema change]
```

### 8.3 Prompt Library — Top 10 Starters

| # | Persona | Prompt |
|---|---|---|
| 1 | Dev | `"Generate JUnit 5 + Mockito tests for all public methods in [ClassName]. Use Testcontainers for DB calls."` |
| 2 | Dev | `"Refactor this class to follow Hexagonal Architecture. Show before/after."` |
| 3 | Dev | `"Explain what this COBOL program does in plain English, then list its external dependencies."` |
| 4 | BA | `"Convert these meeting notes into 5 user stories with Gherkin acceptance criteria: [paste notes]"` |
| 5 | BA | `"Identify gaps between this BRD and these Jira stories: [paste both]"` |
| 6 | QA | `"Given this OpenAPI spec, generate a Postman collection with happy path and error cases."` |
| 7 | QA | `"Write Cypress tests for these acceptance criteria: [paste AC]. Use Page Object Model."` |
| 8 | PM | `"Summarise this sprint for an executive audience in 3 paragraphs. Data: [paste Jira export]"` |
| 9 | Coach | `"Synthesise these retro sticky notes into themes, insights and action items: [paste notes]"` |
| 10 | All | `"Review this output for accuracy and flag anything you're uncertain about."` (Always end with this) |

---

## 9. Success Metrics

### 9.1 Developer Productivity

| Metric | Baseline | 3-month target | 6-month target |
|---|---|---|---|
| PR cycle time (open → merge) | Measure now | -20% | -35% |
| Boilerplate lines per sprint | Measure now | -40% | -60% |
| Unit test coverage delta | Measure now | +10% | +20% |
| Time to first commit on new feature | Measure now | -30% | -50% |

### 9.2 Quality

| Metric | Baseline | Target |
|---|---|---|
| Bug escape rate to UAT | Measure now | -25% at 6 months |
| OWASP-flagged PRs | Measure now | -40% at 6 months |
| Story rejection rate (BA → Dev) | Measure now | -30% at 3 months |

### 9.3 Adoption

| Metric | Target |
|---|---|
| % devs using Claude Code weekly | 80% by week 10 |
| % BAs using prompt library | 70% by week 12 |
| Prompt library prompts used | > 100 uses/week by week 16 |
| Governance policy violations | < 5/month |

---

## 10. Appendix

### A. Technology Stack for APEX Platform

```
APEX Core Infrastructure (AWS-native, fits your background):

API Gateway → Lambda → Claude API          (automation bridge)
Lambda → Jira REST API                     (Jira integration)
Lambda → Confluence REST API               (doc automation)
S3 + CloudWatch                            (audit log storage)
AWS Comprehend                             (PII guard)
DynamoDB                                   (prompt library, config store)
CloudFront + S3                            (APEX Portal static hosting)
Secrets Manager                            (API keys)
GitHub Actions                             (CI/CD AI gates)
```

### B. Estimated Build Effort

| Component | Effort | Priority |
|---|---|---|
| CLAUDE.md templates | 2 days | P0 |
| Dev onboarding workshop | 3 days | P0 |
| Prompt Library v1 (Confluence) | 3 days | P0 |
| BA/PM/QA workshops | 3 days | P1 |
| Jira → Claude automation (1 trigger) | 3 days | P1 |
| AI CI/CD gates (PR review) | 4 days | P1 |
| APEX Portal v1 | 5 days | P2 |
| Governance Dashboard v1 | 5 days | P2 |
| PII Guard | 4 days | P2 |
| Full audit log pipeline | 5 days | P2 |
| Mainframe analysis pipeline | 8 days | P3 |
| **Total** | **~45 dev-days** | |

### C. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Developer resistance | Medium | High | Champion-led rollout; address IP fears early |
| AI hallucinations in production | Low | High | All AI output reviewed before commit |
| PII leak via prompt | Low | Critical | PII Guard pre-prompt scanning |
| API rate limits | Medium | Medium | Retry logic + fallback; cache common prompts |
| Licence cost overrun | Low | Medium | Monitor token usage; use Haiku for automation, Sonnet for complex tasks |
| Skill gap in AI Platform Engineer | Medium | High | Hire or train early; Claude Code is well-documented |

---

*APEX Framework v1.0 — Prepared for enterprise Angular/Java/Mainframe SDLC augmentation*
*Tools: Claude Code (Anthropic) · GitHub Copilot (Microsoft) · Claude API*
