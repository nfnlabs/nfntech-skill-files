---
name: testing
description: Backend test suites — unit test structure, mocking external dependencies, coverage targets by path criticality, assertions, and CI gates. Read when adding tests, raising coverage, or fixing a flaky test.
---

# Testing

> A test earns its place by failing when the behavior breaks. Mock external dependencies
> only; nothing hits a real network, DB, or clock in a unit test.

Business logic under test lives in services, not controllers → `architecture.md`. Reviewing
test coverage on a PR → `code-review.md`.

## 1 · Principles

Arrange-Act-Assert. One assertion per test (or related assertions on one concept). Test
behavior/output, not implementation details. Unit tests are fast (no network/DB, ideally
under 100ms each) and isolated — no shared state between tests, no test depends on another's
side effects. Test names describe what's being tested.

```js
// Bad                          // Good
it('works', () => {...});       it('should return 0 for empty items', () => {...});
it('test1', () => {...});       it('should throw error if item price is negative', () => {...});
```

## 2 · Coverage targets

| Path type | Target |
|---|---|
| Critical (auth, payments, data mutations) | ≥80% |
| Standard business logic | ≥70% |
| Utilities/helpers | ≥80% |
| Controllers (HTTP layer) | ≥60% — prefer integration tests here |

Every endpoint needs at minimum: one happy-path test, one validation-failure test, one
auth-failure test (if protected), one not-found/edge-case test. Test business logic
independent of the HTTP layer wherever the architecture allows it — unit test the service
function, not just the route.

## 3 · Mocking & isolation

Mock external dependencies (DB, third-party APIs) — never call them for real in a unit test.
Use a real (containerized/in-memory) database for integration tests instead of mocking the
DB — a mocked-DB test can pass while the real query is broken.

```js
describe('userService.getUser', () => {
  let userRepository;
  beforeEach(() => {
    userRepository = { findById: jest.fn().mockResolvedValue({ id: 1, name: 'Alice' }) };
  });

  it('should fetch user from repository', async () => {
    const userService = new UserService(userRepository);
    const user = await userService.getUser(1);
    expect(user.id).toBe(1);
    expect(userRepository.findById).toHaveBeenCalledWith(1);
  });
});
```

```js
const mockGateway = { processPayment: jest.fn() };

it('should throw error if gateway fails', async () => {
  mockGateway.processPayment.mockRejectedValue(new Error('Timeout'));
  const service = new PaymentService(mockGateway);
  await expect(service.charge({ amount: 100 })).rejects.toThrow();
});
```

## 4 · What to cover

Happy path, unhappy paths (invalid input, downstream failure, timeout), and edge cases
(null, empty, boundary values):

```js
it('should throw error if customer does not exist', async () => {
  await expect(orderService.create({ customerId: 999, items: [] }))
    .rejects.toThrow('Customer not found');
});

it('should handle very large quantities', () => {
  const total = orderService.calculateTotal([{ price: 100, qty: 999999 }]);
  expect(total).toBe(99999900);
});
```

Avoid brittle assertions — assert what matters, not the whole shape:

```js
// Bad — breaks on any unrelated field change
expect(user).toEqual({ id: 1, name: 'Alice', email: 'a@x.com', createdAt: '...', updatedAt: '...' });

// Good
expect(user).toEqual(expect.objectContaining({ id: 1, name: 'Alice', email: 'a@x.com' }));
```

## 5 · Fixture factories

```js
function createMockUser(overrides = {}) {
  return { id: 1, name: 'Alice', email: 'alice@example.com', isActive: true, ...overrides };
}

it('should handle inactive user', () => {
  expect(userService.getDiscount(createMockUser({ isActive: false }))).toBe(0);
});
```

Adding a required field to the model then touches one factory instead of every call site —
this is the single biggest reason test suites get abandoned halfway through a project.

## 6 · Common mistakes

| Mistake | Issue | Fix |
|---|---|---|
| Testing implementation | asserting internal calls instead of output | test public behavior/output |
| Shared state between tests | tests affect each other | reset state in `beforeEach` |
| Brittle assertions | breaks on unrelated refactors | assert on behavior, not the whole shape |
| Only happy path tested | unhappy paths and edge cases ship unverified | add failure and boundary tests |
| Mocking too much | ends up testing the mocks, not the code | mock only external dependencies |
| Slow tests | real I/O in a unit test | mock it; keep integration tests separate |
| `console.log`/no assertions | test doesn't actually verify anything | assert on the real output |

## 7 · CI gates

```bash
npm test                          # or the project's test runner
npm test -- --coverage
```

Run tests, linter, and a dependency/security audit in CI on every change, not just locally.
Strip generated/vendor files from coverage or the number is meaningless.

## 8 · Done when

- New behavior has a test that fails before the fix and passes after
- Coverage on the changed critical path meets the target above
- Happy path plus at least two unhappy paths covered per new function/endpoint
- No test hits a real network, DB, or depends on another test's side effects
- Suite passes from a clean run, and passes twice in a row (not flaky)
