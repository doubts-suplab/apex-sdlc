# Prompt: Test Case Generation (QA / Tester)
# APEX Prompt Library · Category: QA · Tool: Claude Code CLI + VS Code

---

## AC → Cypress E2E Tests (Page Object Model)

```
Write Cypress E2E tests using Page Object Model for these acceptance criteria.

Structure:
1. Page Object class with typed selectors (data-testid attributes)
2. Test spec using the Page Object
3. Fixtures for API stubs (cy.intercept)

For each AC scenario:
- Happy path test
- Validation error test (if form involved)
- Network error / API failure test

Requirements:
- TypeScript strict mode
- cy.intercept() for ALL API calls — no real network calls in tests
- Custom Cypress commands for repeated flows (login, navigation)
- Assertions on: URL, page content, error messages, loading states

Acceptance Criteria:
[PASTE GHERKIN AC HERE]

API endpoints involved (from OpenAPI spec or Swagger):
[PASTE ENDPOINTS]
```

---

## OpenAPI → Postman Collection

```
Generate a Postman Collection (v2.1 JSON) from this OpenAPI 3.0 spec.

For each endpoint include:
- Happy path request with realistic example data
- 400 Bad Request (missing required field)
- 400 Bad Request (invalid field format)
- 401 Unauthorized (missing/invalid token)
- 404 Not Found (where applicable)
- 500 Internal Server Error (for documentation — use mock)

Collection variables:
- {{baseUrl}} — set to environment variable
- {{authToken}} — set via pre-request script from login endpoint
- {{testEntityId}} — set from create response for use in get/update/delete

Include: Pre-request scripts for token refresh, Test scripts for status code + response body assertions.

OpenAPI Spec:
[PASTE YAML/JSON]
```

---

## Edge Case Generator

```
Given these acceptance criteria and the system context, identify all edge cases
a QA engineer should test that are NOT covered by the happy path.

Categories to consider:
- Boundary values (min, max, min-1, max+1)
- Empty / null / blank inputs
- Special characters and injection strings
- Concurrent requests / race conditions
- Session expiry mid-flow
- Large data volumes (performance edge)
- Internationalisation (unicode, RTL text, date formats)
- Accessibility (keyboard-only navigation, screen reader)
- Mobile viewport (if applicable)

For each edge case:
- Test ID: EC-[number]
- Scenario description
- Expected result
- Risk if not tested: Low / Medium / High

AC:
[PASTE]

System context (stack, data model):
[DESCRIBE]
```

---

## Bug Report → Regression Test

```
A bug was found and fixed. Generate a regression test that would have caught it.

Bug description: [describe the bug, the fix, and the root cause]

Generate:
1. JUnit 5 unit test targeting the fixed method
2. Cypress E2E test covering the user flow that exposed the bug
3. A description of where this test should live in the test suite

The test must fail on the buggy code and pass on the fixed code.
```
