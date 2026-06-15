# Prompt: Refactoring (Developer)
# APEX Prompt Library · Category: Developer · Stack: Java / Spring Boot / Angular

---

## Hexagonal Architecture Refactor

```
Refactor [ClassName] to follow Hexagonal Architecture (Ports & Adapters).

Current state: [describe — e.g. service class directly calls JPA repository and REST client]

Target structure:
- domain/       → pure business logic, no framework annotations
- application/  → use-case orchestration, calls domain + ports
- infrastructure/ → JPA adapter, REST client adapter (implements port interfaces)
- web/          → controller (calls application layer only)

Rules:
- Domain classes have zero Spring annotations
- Port interfaces live in application layer
- Adapters implement ports and live in infrastructure
- Show before/after for each class

[Paste class(es) here]
```

---

## Legacy to Modern Java

```
Modernise this Java code from [Java 8/11] patterns to Java 21.

Apply:
- Records instead of POJOs with getters/setters (where immutable)
- Sealed classes for type hierarchies (where applicable)
- Switch expressions instead of switch statements
- Text blocks for multi-line strings
- var where type is obvious from context
- Stream.toList() instead of .collect(Collectors.toList())
- Optional chains instead of null checks
- Replace javax.* with jakarta.* if Spring Boot 3.x

Do NOT change: method signatures that are part of a public API.
Show diff format: old code → new code per change.

[Paste class here]
```

---

## God Class Decomposition

```
This class violates Single Responsibility. Decompose it.

Steps:
1. Identify all distinct responsibilities (list them)
2. Propose new class names and their single responsibility each
3. Show the decomposed structure (class signatures + method assignments)
4. Show how the original class becomes a thin orchestrator if needed
5. Identify which tests need to be rewritten vs can be kept

Do not write the full implementation — show the design first, then I'll confirm.

[Paste class here]
```

---

## COBOL to Spring Batch Migration

```
Analyse this COBOL batch program and propose a Spring Batch equivalent.

For each COBOL SECTION, map to:
- Spring Batch component (ItemReader / ItemProcessor / ItemWriter / Tasklet)
- Java class name and package
- Input/Output model (Java record or class)
- Business rules to preserve verbatim

Constraints:
- Keep the same transaction boundary as the COBOL COMMIT points
- Flag any COBOL-specific behaviour (FILE STATUS, level-88 conditions) that needs special handling
- Do NOT generate Spring Batch code yet — design review first

[Paste COBOL program here]
```

---

## Angular: Class Component → Standalone Signal Component

```
Convert this Angular NgModule-based component to a standalone component using Signals.

Apply:
- standalone: true
- Replace @Input() with input() signal
- Replace @Output() EventEmitter with output()
- Replace ngOnChanges with effect() or computed()
- Replace subscribe() calls with toSignal()
- Add ChangeDetectionStrategy.OnPush
- Remove NgModule declaration and add imports array directly

Show before/after. Flag any RxJS Observable that cannot be easily converted.

[Paste component here]
```
