# Prompt: Test Generation (Developer)
# APEX Prompt Library · Category: Developer · Stack: Java / Spring Boot / Angular

---

## JUnit 5 — Full Class Test Suite

```
Generate complete JUnit 5 + Mockito 5 tests for [ClassName].

Requirements:
- Use @ExtendWith(MockitoExtension.class)
- Constructor injection — use @InjectMocks and @Mock
- Cover: all public methods, happy path + top 3 error/edge cases each
- Use AssertJ assertions (assertThat, not assertTrue/assertEquals)
- Name tests: should_[expectedBehaviour]_when_[condition]
- For DB interactions: use @Testcontainers + @Container with PostgreSQL image
- For Kafka: use EmbeddedKafkaBroker
- Flag any method that needs an integration test rather than a unit test

[Paste class here]
```

---

## Angular — Jasmine Component Spec

```
Write a Jasmine spec for [ComponentName] (Angular standalone component).

Requirements:
- Use TestBed.configureTestingModule with all required imports
- Mock all injected services with jasmine.createSpyObj
- Test: component creation, input binding, output emissions, conditional rendering
- Use Angular Testing Library queries where possible (getByText, getByRole)
- Test async operations with fakeAsync / tick or async / whenStable
- Verify no console errors during any test

[Paste component here]
```

---

## Cypress E2E from Acceptance Criteria

```
Write Cypress E2E tests using Page Object Model for these acceptance criteria.

AC:
[Paste Gherkin AC here]

Requirements:
- Create a Page Object class with typed selectors
- One describe block per AC scenario
- Use cy.intercept() to stub all API calls with fixture data
- Include: happy path, validation errors, network error state
- Use data-testid attributes for selectors (not CSS classes)
- Add a custom command if a flow is reused across tests
```

---

## Spring Boot Integration Test

```
Write a @SpringBootTest integration test for [ControllerName] using WebTestClient.

Requirements:
- Use @SpringBootTest(webEnvironment = RANDOM_PORT)
- Use @AutoConfigureWebTestClient
- Use Testcontainers for PostgreSQL: @Testcontainers + @Container
- Use @Sql to seed test data from a SQL fixture file
- Test all endpoints: 200 success, 400 validation failure, 404 not found, 401 unauthorized
- Assert response body fields explicitly — not just status codes
- Mock external REST clients with WireMock (@WireMockTest)

[Paste controller signature / OpenAPI spec here]
```

---

## Coverage Gap Filler

```
Run the jacoco-coverage-tester agent on [module path].
Identify all methods below 80% line coverage.
For each uncovered method, generate the minimum test to bring it to 80%.
Group by class. Show which tests already exist vs which need to be added.
```
