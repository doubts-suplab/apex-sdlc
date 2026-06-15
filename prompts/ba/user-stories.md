# Prompt: User Story Generation (Business Analyst)
# APEX Prompt Library · Category: BA · Tool: Claude.ai Desktop

---

## Meeting Notes → Jira User Stories

```
You are a Business Analyst on an enterprise Java/Angular project.

I will paste meeting notes or a stakeholder conversation.
Convert them into well-structured Jira user stories.

For each story produce:
- **Title**: [verb] + [object] + [context] (e.g. "Filter transaction list by date range")
- **User Story**: As a [persona], I want to [action] so that [business value]
- **Acceptance Criteria** (Gherkin):
  Given [precondition]
  When [action]
  Then [outcome]
  And [additional outcome if needed]
- **Story Points**: [1 / 2 / 3 / 5 / 8] with rationale
- **Dependencies**: [other stories this blocks or is blocked by]
- **Out of scope**: [what this story explicitly does NOT cover]

Label each story with: [Feature name] | [Epic name] | [Sprint target if mentioned]

After all stories: flag any ambiguities you spotted that need BA clarification before dev picks up.

Meeting notes:
[PASTE HERE]
```

---

## Epic → Feature Breakdown

```
Break this Epic into Features, then Features into User Stories.

Epic: [Epic title and description]

For each Feature:
- Feature name + one-line description
- Estimated story count
- List of User Stories (title only at this stage)
- Dependencies between features

Then for the highest-priority feature, generate full user stories with Gherkin AC.

Target sprint capacity: [X story points per sprint]
Team size: [N developers + N QAs]
```

---

## Acceptance Criteria Validator

```
Review these user stories and acceptance criteria.

For each story check:
- Is the user story in correct "As a / I want / So that" format?
- Are acceptance criteria testable (can a QA write a test for each one)?
- Are there missing edge cases (empty state, error state, max input)?
- Are there conflicting criteria?
- Is the scope clear enough for a developer to estimate?

Flag: ambiguous, incomplete, or untestable criteria.
Suggest: improved phrasing for each flagged item.

Stories:
[PASTE HERE]
```

---

## BRD → User Story Extraction

```
Read this Business Requirements Document section and extract all implicit user stories.

For each requirement:
1. Identify the user persona affected
2. Write the user story
3. Write 3 acceptance criteria in Gherkin
4. Flag non-functional requirements (performance, security, accessibility) separately

Then create an epic structure grouping related stories.

BRD section:
[PASTE HERE]
```
