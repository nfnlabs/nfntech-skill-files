---
name: backend-unit-testing
description: Unit testing standards for backend systems — test structure, mocking, assertions, coverage targets, and practical examples for Node.js/TypeScript.
triggers:
  - user
  - model
---

# Backend Unit Testing Standards

You are a senior test engineer. Write tests that catch bugs, document behavior, and give confidence in refactoring. Tests should be fast, isolated, and maintainable.

---

## 0. Testing Principles

- **Arrange-Act-Assert**: Setup → Execute → Verify
- **One assertion per test** (or related assertions on same concept)
- **Test behavior, not implementation**: Mock internals, verify outputs
- **Fast**: Unit tests run in milliseconds, no network/DB calls
- **Isolated**: Each test independent, no shared state
- **Readable**: Test name describes what is being tested
- **Maintainable**: Easy to update when behavior changes

---

## 1. Test Structure

### Basic Pattern

```js
describe('orderService.calculateTotal', () => {
  // Setup
  beforeEach(() => {
    // Initialize test data
  });

  afterEach(() => {
    // Cleanup
  });

  // Happy path
  it('should calculate total for valid items', () => {
    const items = [
      { price: 10, qty: 2 },
      { price: 5, qty: 3 }
    ];
    const total = orderService.calculateTotal(items);
    expect(total).toBe(35);
  });

  // Unhappy path
  it('should return 0 for empty items', () => {
    const total = orderService.calculateTotal([]);
    expect(total).toBe(0);
  });

  // Edge case
  it('should handle null items', () => {
    const total = orderService.calculateTotal(null);
    expect(total).toBe(0);
  });
});
```

### Naming Convention

Test names should be clear and descriptive.

```js
// Bad
it('works', () => { ... });
it('test1', () => { ... });

// Good
it('should calculate total for valid items', () => { ... });
it('should return 0 for empty items', () => { ... });
it('should throw error if item price is negative', () => { ... });
```

---

## 2. Mocking & Isolation

### Mock External Dependencies

Never call real APIs, databases, or external services in unit tests.

```js
// Bad — calls real database
describe('userService.getUser', () => {
  it('should fetch user from database', async () => {
    const user = await userService.getUser(1);
    expect(user.id).toBe(1);
  });
});

// Good — mocks database
describe('userService.getUser', () => {
  let userRepository;

  beforeEach(() => {
    userRepository = {
      findById: jest.fn().mockResolvedValue({ id: 1, name: 'Alice' })
    };
  });

  it('should fetch user from repository', async () => {
    const userService = new UserService(userRepository);
    const user = await userService.getUser(1);
    expect(user.id).toBe(1);
    expect(userRepository.findById).toHaveBeenCalledWith(1);
  });
});
```

### Mock Return Values

```js
// Setup mock to return different values
const mockDb = {
  query: jest.fn()
    .mockResolvedValueOnce([{ id: 1 }])  // First call
    .mockResolvedValueOnce([])            // Second call
    .mockRejectedValueOnce(new Error('Connection failed')) // Third call
};
```

### Verify Mock Calls

```js
it('should call repository with correct parameters', async () => {
  const mockRepo = { save: jest.fn().mockResolvedValue({ id: 1 }) };
  const service = new OrderService(mockRepo);

  await service.create({ items: [{ sku: 'ABC' }] });

  expect(mockRepo.save).toHaveBeenCalledWith(
    expect.objectContaining({ items: expect.any(Array) })
  );
  expect(mockRepo.save).toHaveBeenCalledTimes(1);
});
```

---

## 3. Test Coverage

### Coverage Targets

| Path Type | Target | Example |
|---|---|---|
| Critical (auth, payments, data mutations) | ≥80% | Payment processing, user creation |
| Standard business logic | ≥70% | Order calculation, discount logic |
| Utilities/helpers | ≥80% | Date formatting, validation |
| Controllers | ≥60% | HTTP layer (integration tests preferred) |

### What to Cover

**Happy Path**: Normal, expected flow.

```js
it('should create order with valid input', async () => {
  const order = await orderService.create({
    customerId: 1,
    items: [{ sku: 'ABC', qty: 2 }]
  });
  expect(order.id).toBeDefined();
  expect(order.total).toBe(expectedTotal);
});
```

**Unhappy Paths**: Invalid input, errors, edge cases.

```js
it('should throw error if customer does not exist', async () => {
  await expect(
    orderService.create({ customerId: 999, items: [] })
  ).rejects.toThrow('Customer not found');
});

it('should throw error if items array is empty', async () => {
  await expect(
    orderService.create({ customerId: 1, items: [] })
  ).rejects.toThrow('At least one item required');
});
```

**Edge Cases**: Null, empty, boundary values, timeouts.

```js
it('should handle null items gracefully', () => {
  const total = orderService.calculateTotal(null);
  expect(total).toBe(0);
});

it('should handle very large quantities', () => {
  const items = [{ price: 100, qty: 999999 }];
  const total = orderService.calculateTotal(items);
  expect(total).toBe(99999900);
});
```

---

## 4. Assertions

### Common Assertions

```js
// Equality
expect(value).toBe(5);
expect(value).toEqual({ id: 1, name: 'Alice' });

// Truthiness
expect(value).toBeTruthy();
expect(value).toBeFalsy();
expect(value).toBeNull();
expect(value).toBeUndefined();

// Numbers
expect(value).toBeGreaterThan(5);
expect(value).toBeLessThan(10);
expect(value).toBeCloseTo(3.14, 2);

// Strings
expect(message).toContain('error');
expect(message).toMatch(/invalid/i);

// Arrays
expect(array).toHaveLength(3);
expect(array).toContain('item');
expect(array).toEqual(expect.arrayContaining([1, 2]));

// Objects
expect(obj).toHaveProperty('id');
expect(obj).toEqual(expect.objectContaining({ id: 1 }));

// Errors
expect(() => fn()).toThrow();
expect(() => fn()).toThrow('specific message');
expect(async () => await fn()).rejects.toThrow();

// Functions
expect(mockFn).toHaveBeenCalled();
expect(mockFn).toHaveBeenCalledWith(arg1, arg2);
expect(mockFn).toHaveBeenCalledTimes(2);
```

### Avoid Brittle Assertions

```js
// Bad — too specific, breaks with minor changes
expect(user).toEqual({
  id: 1,
  name: 'Alice',
  email: 'alice@example.com',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z'
});

// Good — test what matters
expect(user).toEqual(expect.objectContaining({
  id: 1,
  name: 'Alice',
  email: 'alice@example.com'
}));
```

---

## 5. Test Organization

### Group Related Tests

```js
describe('orderService', () => {
  describe('calculateTotal', () => {
    it('should calculate total for valid items', () => { ... });
    it('should return 0 for empty items', () => { ... });
  });

  describe('create', () => {
    it('should create order with valid input', () => { ... });
    it('should throw error if customer not found', () => { ... });
  });

  describe('cancel', () => {
    it('should cancel pending order', () => { ... });
    it('should throw error if order already shipped', () => { ... });
  });
});
```

### Setup & Teardown

```js
describe('userService', () => {
  let userService;
  let mockRepository;

  beforeAll(() => {
    // Run once before all tests
  });

  beforeEach(() => {
    // Run before each test
    mockRepository = { findById: jest.fn() };
    userService = new UserService(mockRepository);
  });

  afterEach(() => {
    // Run after each test
    jest.clearAllMocks();
  });

  afterAll(() => {
    // Run once after all tests
  });
});
```

---

## 6. Practical Examples

### Testing Async Operations

```js
describe('paymentService.charge', () => {
  let mockGateway;

  beforeEach(() => {
    mockGateway = { processPayment: jest.fn() };
  });

  it('should charge card successfully', async () => {
    mockGateway.processPayment.mockResolvedValue({ transactionId: 'tx_123' });
    const service = new PaymentService(mockGateway);

    const result = await service.charge({ amount: 100, cardToken: 'tok_abc' });

    expect(result.transactionId).toBe('tx_123');
    expect(mockGateway.processPayment).toHaveBeenCalledWith({
      amount: 100,
      cardToken: 'tok_abc'
    });
  });

  it('should throw error if gateway fails', async () => {
    mockGateway.processPayment.mockRejectedValue(new Error('Timeout'));
    const service = new PaymentService(mockGateway);

    await expect(
      service.charge({ amount: 100, cardToken: 'tok_abc' })
    ).rejects.toThrow();
  });
});
```

### Testing Validation & Error Handling

```js
describe('orderService.create', () => {
  it('should reject empty items', async () => {
    await expect(
      orderService.create({ customerId: 1, items: [] })
    ).rejects.toThrow('At least one item required');
  });

  it('should reject if customer not found', async () => {
    await expect(
      orderService.create({ customerId: 999, items: [{ sku: 'ABC' }] })
    ).rejects.toThrow('Customer not found');
  });

  it('should create order with valid input', async () => {
    const order = await orderService.create({
      customerId: 1,
      items: [{ sku: 'ABC', qty: 2 }]
    });
    expect(order.id).toBeDefined();
  });
});
```

---

## 7. Test Utilities & Helpers

### Factory Functions

```js
// Create test data consistently
function createMockUser(overrides = {}) {
  return {
    id: 1,
    name: 'Alice',
    email: 'alice@example.com',
    isActive: true,
    ...overrides
  };
}

// Usage
it('should handle inactive user', () => {
  const user = createMockUser({ isActive: false });
  expect(userService.getDiscount(user)).toBe(0);
});
```

### Assertion Helpers

```js
// Reusable assertion logic
function expectValidOrder(order) {
  expect(order).toHaveProperty('id');
  expect(order).toHaveProperty('total');
  expect(order.total).toBeGreaterThan(0);
  expect(order.createdAt).toBeInstanceOf(Date);
}

// Usage
it('should create valid order', async () => {
  const order = await orderService.create({ items: [...] });
  expectValidOrder(order);
});
```

---

## 8. Common Testing Mistakes

| Mistake | Issue | Fix |
|---|---|---|
| Testing implementation | `expect(mockFn).toHaveBeenCalledWith(...)` for internal calls | Test public behavior/output instead |
| Shared state between tests | Tests affect each other | Use `beforeEach` to reset state |
| Brittle assertions | Test breaks with minor refactors | Assert on behavior, not implementation |
| No error testing | Only happy path tested | Add unhappy path and edge case tests |
| Mocking too much | Mock everything, test nothing | Mock only external dependencies |
| Slow tests | Tests take seconds | Avoid real I/O, use mocks |
| Unclear test names | Hard to understand what's being tested | Use descriptive names |
| Too many assertions | Hard to debug failures | One concept per test |
| No setup/teardown | Tests pollute each other | Use `beforeEach`/`afterEach` |

---

## 9. Running Tests

### Common Commands

```bash
# Run all tests
npm test

# Run tests in watch mode (re-run on file change)
npm test -- --watch

# Run specific test file
npm test -- userService.test.js

# Run tests matching pattern
npm test -- --testNamePattern="should calculate"

# Run with coverage
npm test -- --coverage

# Run with verbose output
npm test -- --verbose
```

### Coverage Report

```bash
npm test -- --coverage

# Output example:
# -------|----------|----------|----------|----------|
# File   | % Stmts  | % Branch | % Funcs  | % Lines  |
# -------|----------|----------|----------|----------|
# All    | 85.2     | 78.5     | 90.1     | 85.2     |
```

---

## 10. Test Checklist

Before committing tests:

- [ ] Test name clearly describes what is being tested
- [ ] Happy path covered
- [ ] At least 2 unhappy paths covered
- [ ] Edge cases covered (null, empty, boundary)
- [ ] Mocks verify correct calls
- [ ] No real network/DB calls
- [ ] No shared state between tests
- [ ] Tests are fast (< 100ms each)
- [ ] Assertions are clear and specific
- [ ] No brittle implementation-detail assertions
- [ ] Coverage ≥70% for critical paths

