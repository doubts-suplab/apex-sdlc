# Prompt: COBOL & Mainframe Analysis (Developer)
# APEX Prompt Library · Category: Developer · Stack: Mainframe
# GOVERNANCE: Analysis only until Mainframe Gate approved (Week 17)

---

## Program Explainer (Start here for any unknown program)

```
Explain what this COBOL program does in plain English.

Structure your answer as:
1. **Purpose** — what business problem does this solve? (2 sentences)
2. **Inputs** — datasets read, queues consumed, DB2 tables selected
3. **Outputs** — datasets written, queues published, DB2 tables updated/inserted
4. **Processing logic** — step-by-step in plain English (no COBOL syntax)
5. **External dependencies** — CALL statements, EXEC CICS, EXEC SQL, COPY books
6. **Error handling** — FILE-STATUS checks, SQLCODE handling, abend points
7. **Restart/recovery** — checkpoint logic, restart conditions
8. **Migration complexity** — Low / Medium / High + reason

[Paste COBOL program here]
```

---

## Copybook to Java DTO

```
Convert this COBOL copybook to a Java record (Java 21).

Rules:
- PIC X(n)   → String (trim whitespace on read)
- PIC 9(n)   → int or long depending on size
- PIC 9(n)V99 → BigDecimal (never float/double for financial)
- PIC 9(8) YYYYMMDD → LocalDate (with conversion note)
- PIC 9(6) HHMMSS   → LocalTime (with conversion note)
- COMP-3 / PACKED-DECIMAL → BigDecimal
- Level-88 conditions → Java enum (list the values)
- Nested group items → nested Java record

Include: conversion utility methods for date/numeric fields.
Flag: any field whose semantics are ambiguous from the copybook alone.

[Paste copybook here]
```

---

## JCL Decoder

```
Explain this JCL job in plain English.

For each step:
- What program/utility runs (EXEC PGM=...)
- What datasets it reads (DD DISP=SHR)
- What datasets it writes or creates (DD DISP=(NEW,CATLG))
- What it produces (output dataset names and formats)
- Dependencies on previous steps (COND parameters)

Then:
- Draw the job flow as a text diagram (Step1 → Step2 → Step3)
- Identify the restart point if Step 3 abends
- Flag any SORT steps with their sort keys

[Paste JCL here]
```

---

## Migration Readiness Assessment

```
Assess the migration readiness of this COBOL program for rewrite as a Spring Boot / Spring Batch service.

Score each dimension 1–5 (1=easy, 5=hard):
- Business logic complexity
- External dependency count (CALL, CICS, MQ)
- Data model complexity (VSAM, DB2, file formats)
- Test coverage (existing test harness?)
- COBOL-specific behaviour (COMP-3, REDEFINES, ALTER)

Overall: Low / Medium / High complexity

Recommended approach:
- [ ] Direct rewrite (Low complexity)
- [ ] Strangler Fig via MQ bridge (Medium)
- [ ] Keep on mainframe, expose via API gateway (High / mission-critical)

Estimated effort: [use APEX estimation formula: raw hours ÷ 6.4]

[Paste COBOL program here]
```

---

## Runbook Generator

```
Generate a runbook for this COBOL batch job.

Sections:
## Overview
## Schedule & Trigger
## Prerequisites (datasets, DB2 grants, MQ queues)
## Input Datasets (name, format, record layout)
## Output Datasets (name, format, retention)
## Step-by-Step Execution
## Restart Procedure (from each step)
## Common Abend Codes and Resolution
## Escalation Path
## Change History

[Paste COBOL program + JCL here]
```
