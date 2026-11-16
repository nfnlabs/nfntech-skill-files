---
name: testing
description: Backend test suites — unit and integration tests, mocking external dependencies, coverage targets, security and money-path tests, and CI gates. Read when adding tests, raising coverage, or fixing a flaky test.
---

# Testing

> A test earns its place by failing when the behavior breaks. Mock external dependencies
> only. A unit test never touches a real network, DB or clock.

Business logic under test lives in services → `architecture.md`. Reviewing test coverage on a PR → `code-review.md`.

## 1 · Unit tests

- Arrange-Act-Assert, one concept per test. Assert behavior and output, not internal calls.
- Keep them fast (ideally under 100 ms), isolated, and free of shared state. Reset state in `beforeEach`.
- Name tests for what they check: `should throw if item price is negative`, not `works` or `test1`.
- Mock external dependencies (DB, third-party APIs, payment gateways) and inject them through constructors.
- Assert the fields that matter, not the whole object, so unrelated changes don't break the test.
- Use fixture factories (`createMockUser(overrides)`). Adding a required field then touches one factory, not every call site. This is the most common reason test suites get abandoned.

## 2 · Integration tests

- Use a real containerized or in-memory database. A mocked-DB test can pass while the real query is broken.
- Test endpoints through the HTTP layer.
- Each endpoint needs at least: one happy path, one validation failure, one auth failure (if protected), and one not-found or edge case.
- Cover happy paths, unhappy paths (invalid input, downstream failure, timeout) and edge cases (null, empty, boundary values).

## 3 · Coverage targets

| Path type | Target |
|---|---|
| Critical: auth, payments, data mutations | ≥80% |
| Standard business logic | ≥70% |
| Utilities and helpers | ≥80% |
| Controllers (HTTP layer) | ≥60%; prefer integration tests here |

Strip generated and vendor files from coverage, or the number means nothing.

## 4 · Security and money paths

Mocks can't show who can do what, or how many times something happens. These need
integration tests against a real database:

- **A regression test for every security fix** that fails on the old code. Examples: a forged token is rejected, a cross-tenant request returns 404, a replayed webhook credits once.
- **An authorization matrix per protected resource:** owner ✓, other user in the same tenant ✗, user in another tenant ✗, wrong token kind ✗, no token ✗. IDOR bugs live in the rows nobody wrote.
- **Concurrency:** fire N parallel requests at a balance of 1, and assert exactly one succeeds and the balance ends at 0 (`data-layer.md` §5).
- **Idempotency:** deliver the same webhook or confirmation twice, and assert one effect.
- **Outbound URLs:** private, loopback and metadata addresses are refused (`security.md` §9).

Asserting the SQL text of an atomic update with a regex proves the text, not the behavior.

## 5 · CI and done

Run tests, the linter and a dependency audit in CI on every change, not just locally.

- New behavior has a test that fails before the fix and passes after it.
- Security and money paths have the authorization matrix, concurrency and idempotency tests above.
- Coverage on the changed critical path meets the target.
- No test touches a real network or DB, or depends on another test's side effects.
- The suite passes from a clean run, and passes twice in a row. A flaky test is a bug.
