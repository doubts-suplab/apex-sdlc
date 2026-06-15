# APEX Mainframe Gate Policy
**Version:** 1.0 | **Owner:** Enterprise Architect + ARB | **Classification:** INTERNAL

---

## Overview

Mainframe systems (IBM COBOL, CICS, DB2 z/OS, IBM i) carry the highest risk in any AI-augmented SDLC. A single incorrect generated instruction passed to production JCL or COBOL can trigger batch abends, corrupt VSAM datasets, or silently produce wrong financial outputs.

This policy defines the **Mainframe Gate**: a phased, approval-controlled pathway that permits AI assistance on mainframe work to expand only after each gate is passed.

---

## Gate Phases

### 🔴 Phase 0 — Analysis Only (Default / Current State)
**Status: ACTIVE until ARB approves Phase 1**

What AI MAY do:
- Explain existing COBOL programs in plain English
- Decode JCL steps and VSAM structures
- Convert COBOL copybooks to Java DTOs (for documentation only)
- Generate runbooks from existing programs
- Assess migration complexity (Low / Medium / High scoring)
- Produce data flow diagrams from batch job chains

What AI MUST NOT do:
- Generate new COBOL, JCL, or RPG code
- Suggest modifications to existing programs
- Produce DB2 DDL or DML for z/OS
- Generate CICS transaction definitions
- Create or modify VSAM cluster definitions
- Recommend changes to sort cards or DFSORT parameters

**Enforcement:** The `claude-templates/mainframe/CLAUDE.md` contains a hard STOP at the top of all permitted prompts. The `code-reviewer` agent will reject any PR containing generated mainframe code during this phase.

---

### 🟡 Phase 1 — Assisted Analysis + Draft Generation (Gated)
**Trigger: ARB approval + completion of APEX Week 17 criteria**

**Week 17 criteria (all must be met):**
- [ ] At least 20 COBOL programs documented via Phase 0 AI analysis
- [ ] Mainframe dev team has completed APEX AI literacy training (2-hour session)
- [ ] At least 2 copybook-to-Java-DTO conversions validated end-to-end by mainframe architect
- [ ] PII guard enabled and tested on all mainframe-adjacent prompts
- [ ] Security guild has reviewed mainframe prompt library and approved

What AI MAY additionally do in Phase 1:
- Generate **draft** COBOL code with explicit human-review requirement before ANY compilation
- Suggest JCL modifications with diff-style output for mainframe developer review
- Generate RPG IV stubs for IBM i modernisation (ILE patterns only)
- Produce DB2 query drafts (read-only SELECT statements only)

What still requires mainframe developer sign-off before any action:
- All generated or modified COBOL (line-by-line review required)
- Any JCL change touching production datasets (DISP=OLD or DISP=SHR on prod)
- Any DB2 DDL or UPDATE/INSERT/DELETE

---

### 🟢 Phase 2 — Full Assisted Modernisation (Future State)
**Trigger: Successful Phase 1 for minimum 2 sprints + ARB sign-off**

What AI MAY additionally do in Phase 2:
- Generate Spring Batch job equivalents from analysed COBOL batch programs
- Generate Liquibase migration scripts from DB2 z/OS DDL
- Produce full migration readiness reports with effort estimates
- Assist with Strangler Fig pattern implementation (MQ bridge stubs)

Phase 2 still requires:
- Full mainframe architect sign-off on any program migrated off-platform
- ARB approval for each bounded context migrated
- Parallel-run testing (mainframe vs. new service) for minimum 2 weeks

---

## Escalation Path

```
Developer spots an AI suggestion that may violate this policy
    ↓
Raise in #apex-governance Slack channel (tag @tech-lead)
    ↓
Tech Lead reviews within 1 business day
    ↓
If mainframe-specific: escalates to Enterprise Architect
    ↓
ARB reviews at next fortnightly meeting
    ↓
ARB decision logged in Confluence: APEX → ARB Decisions
```

---

## Audit Trail

Every AI interaction with mainframe-related prompts is logged:

| Log item | Location |
|---|---|
| All prompts sent to Claude involving COBOL/JCL/RPG | CloudWatch Logs group: `/apex/mainframe-prompts` |
| Phase gate approval decisions | Confluence: APEX → Governance → Mainframe Gate Log |
| Any mainframe code reviewed (Phase 1+) | GitHub PR with label `mainframe-ai-assisted` |

---

## Current Gate Status

| Gate | Status | Target Date | Approver |
|---|---|---|---|
| Phase 0 — Analysis Only | ✅ ACTIVE | — | Auto (policy default) |
| Phase 1 — Draft Generation | ⏳ Pending | APEX Week 17 | ARB |
| Phase 2 — Full Modernisation | ⏳ Pending | TBD post Phase 1 | ARB + EA |

**Last reviewed:** See git log on this file  
**Next review:** APEX Week 17 ARB meeting
