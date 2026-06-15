# Prompt: Gap Analysis (Business Analyst)
# APEX Prompt Library · Category: BA · Tool: Claude.ai Desktop

---

## BRD vs Jira Stories — Gap Finder

```
Compare this BRD section with these Jira user stories.

Identify:
1. **Missing requirements** — BRD requirements with no corresponding story
2. **Ambiguous AC** — stories where acceptance criteria are too vague for dev/QA
3. **Scope creep** — stories that go beyond the BRD requirements
4. **Conflicting requirements** — where BRD and stories contradict each other
5. **Non-functional gaps** — performance, accessibility, security requirements in BRD not reflected in stories

Output format:
| Gap Type | BRD Reference | Story (if any) | Recommended Action |

BRD:
[PASTE BRD SECTION]

Jira Stories (export or paste):
[PASTE STORIES]
```

---

## As-Is vs To-Be Process Gap

```
Analyse the difference between the current (As-Is) and future (To-Be) process.

For each difference:
- What changes for which persona
- What system changes are implied (UI, API, DB, integration)
- What training or communication is needed
- Risk if gap is not addressed before go-live

Then: identify the top 3 highest-risk gaps and recommend mitigation.

As-Is process:
[PASTE]

To-Be process:
[PASTE]
```

---

## API Contract vs Story Alignment

```
Check whether the OpenAPI specification aligns with the user stories and acceptance criteria.

For each endpoint in the spec:
- Is there a user story that drives it?
- Do the request/response fields cover all acceptance criteria?
- Are error responses (400, 401, 404, 500) documented for each AC error case?

Flag: endpoints with no story (gold-plating), stories with no endpoint (missing API), AC that can't be verified via the API.

OpenAPI spec:
[PASTE YAML or JSON]

User stories:
[PASTE]
```
