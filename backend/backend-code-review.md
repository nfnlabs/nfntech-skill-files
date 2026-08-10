---
name: backend-code-review
description: Code review standards for backend systems — architecture, test coverage, validation, security, and performance checks with practical examples.
triggers:
  - user
  - model
---

# Backend Code Review Standards

You are a senior code reviewer. Evaluate code for correctness, maintainability, security, and performance. Review with respect but rigor — catch issues early, suggest improvements, and explain the reasoning.

---

## 0. Review Checklist

Before approving any PR, verify:

- [ ] No swallowed errors or silent failures
- [ ] All external data (API/DB/SDK) null-checked before use
- [ ] No secrets/keys hardcoded or in logs
- [ ] Input validation at boundaries (params, query, body)
- [ ] Consistent API response shape
- [ ] No N+1 queries or unbounded collection loads
- [ ] Logging includes context, no PII/secrets, correct level
- [ ] No dead code, leftover debug logs, or console.log
- [ ] Existing helpers reused instead of duplicated
- [ ] Tests cover happy path AND unhappy paths
- [ ] Test coverage ≥80% for critical paths
- [ ] No race conditions or concurrency issues
- [ ] Diff is minimal and scoped to the request

---

## 1. Architecture & Design

### Single Responsibility
Each function/class should have one reason to change.

```js
// Bad — mixes validation, business logic, and persistence
async function createOrder(req, res) {
  if (!req.body.items || req.body.items.length === 0) {
    return res.status(400).json({ error: 'No items' });
  }
  const total = req.body.items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const order = new Order({ items: req.body.items, total });
  await order.save();
  res.json({ success: true, data: order });
}

// Good — separated concerns
// Controller
async function createOrder(req, res) {
  const { items } = req.body;
  const order = await orderService.create(items);
  res.json({ success: true, data: order });
}

// Service
async function create(items) {
  validateItems(items);
  const total = calculateTotal(items);
  return await orderRepository.create({ items, total });
}

// Helper
function validateItems(items) {
  if (!items || items.length === 0) {
    throw new ValidationError('At least one item required');
  }
}
```

### Dependency Injection
Avoid tight coupling; inject dependencies.

```js
// Bad — hardcoded dependency
class OrderService {
  constructor() {
    this.db = new Database();
  }
}

// Good — dependency injected
class OrderService {
  constructor(db, logger) {
    this.db = db;
    this.logger = logger;
  }
}
```

---

## 2. Error Handling & Validation

### Fail Fast
Guard clauses prevent nested ifs and make error paths explicit.

```js
// Bad — nested conditions
function processPayment(order) {
  if (order) {
    if (order.amount > 0) {
      if (order.customer) {
        return chargeCard(order);
      } else {
        throw new Error('No customer');
      }
    } else {
      throw new Error('Invalid amount');
    }
  } else {
    throw new Error('No order');
  }
}

// Good — guard clauses
function processPayment(order) {
  if (!order) throw new Error('No order');
  if (order.amount <= 0) throw new Error('Invalid amount');
  if (!order.customer) throw new Error('No customer');
  return chargeCard(order);
}
```

### Meaningful Error Messages
Include context for debugging.

```js
// Bad
throw new Error('Failed');

// Good
throw new PaymentError(`Payment failed for order ${order.id}: ${err.message}`, {
  orderId: order.id,
  amount: order.amount,
  cause: err
});
```

### Null Safety
Always check external data before use.

```js
// Bad — crashes if user is null
const isAdmin = user.role === 'admin';

// Good
if (!user) {
  logger.warn(`User not found for ID ${userId}`);
  return null;
}
const isAdmin = user.role === 'admin';
```

---

## 3. Test Coverage & Quality

- **Critical paths** (auth, payments, data mutations): ≥80% coverage
- **Happy path + 2–3 unhappy paths** per function
- **Edge cases**: null, empty, boundary values, timeouts
- **Avoid**: testing implementation details, mocking too much, brittle assertions
- See `backend-unit-testing` skill for detailed test examples

---

## 4. Database & Queries

### N+1 Detection
Spot loops that query inside iterations.

```js
// Bad — N+1 query
const orders = await Order.find();
for (const order of orders) {
  order.customer = await Customer.findById(order.customerId);
}

// Good — batch/join
const orders = await Order.find().populate('customer');
```

### Indexing
Ensure queries use indexes.

```js
// Bad — no index on status
const pending = await Order.find({ status: 'pending' });

// Good — index exists
// In migration:
CREATE INDEX idx_orders_status ON orders(status);
// Then query is fast
const pending = await Order.find({ status: 'pending' });
```

### Projection
Only fetch needed fields.

```js
// Bad
const users = await User.find();

// Good
const users = await User.find({}, 'id name email');
```

---

## 5. Security

### Input Validation
Validate all boundaries.

```js
// Bad — no validation
app.post('/users/:id', (req, res) => {
  const user = User.findByIdAndUpdate(req.params.id, req.body);
  res.json(user);
});

// Good — validate input
app.post('/users/:id', (req, res) => {
  const schema = z.object({
    name: z.string().min(1).max(100),
    email: z.string().email(),
    age: z.number().int().min(0).max(150)
  });
  const validated = schema.parse(req.body);
  const user = User.findByIdAndUpdate(req.params.id, validated);
  res.json(user);
});
```

### Authorization
Never trust client-supplied IDs.

```js
// Bad — user can edit anyone's profile
app.put('/users/:id', (req, res) => {
  const user = User.findByIdAndUpdate(req.params.id, req.body);
  res.json(user);
});

// Good — verify ownership
app.put('/users/:id', authenticate, (req, res) => {
  if (req.user.id !== parseInt(req.params.id)) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  const user = User.findByIdAndUpdate(req.params.id, req.body);
  res.json(user);
});
```

### Secrets
Never hardcode or log secrets.

```js
// Bad
const apiKey = 'sk_live_abc123';
logger.info(`Using API key: ${apiKey}`);

// Good
const apiKey = process.env.STRIPE_API_KEY;
logger.info('Initializing Stripe');
```

---

## 6. Performance

### Pagination
Prevent unbounded queries.

```js
// Bad — returns all users
app.get('/users', async (req, res) => {
  const users = await User.find();
  res.json(users);
});

// Good — paginated
app.get('/users', async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const limit = Math.min(parseInt(req.query.limit) || 20, 100);
  const users = await User.find()
    .skip((page - 1) * limit)
    .limit(limit);
  res.json({ data: users, page, limit });
});
```

### Caching
Cache expensive operations with invalidation.

```js
// Bad — recalculates every request
app.get('/stats', async (req, res) => {
  const stats = await calculateExpensiveStats();
  res.json(stats);
});

// Good — cache with TTL
const cache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

app.get('/stats', async (req, res) => {
  const cached = cache.get('stats');
  if (cached && Date.now() - cached.time < CACHE_TTL) {
    return res.json(cached.data);
  }
  const stats = await calculateExpensiveStats();
  cache.set('stats', { data: stats, time: Date.now() });
  res.json(stats);
});
```

### Async Operations
Run independent ops in parallel.

```js
// Bad — sequential
const user = await getUser(id);
const orders = await getOrders(id);
const payments = await getPayments(id);

// Good — parallel
const [user, orders, payments] = await Promise.all([
  getUser(id),
  getOrders(id),
  getPayments(id)
]);
```

---

## 7. Logging & Observability

### Structured Logging
Include context, no PII.

```js
// Bad
console.log('Error');
logger.info(`User ${user.email} logged in`);

// Good
logger.error('Payment processing failed', {
  orderId: order.id,
  amount: order.amount,
  errorCode: err.code,
  duration: Date.now() - startTime
});

logger.info('User login successful', {
  userId: user.id,
  duration: Date.now() - startTime
});
```

### Log Levels
Use correctly.

- **debug**: Detailed diagnostic info (variable values, function entry/exit)
- **info**: Significant events (user login, order created)
- **warn**: Unexpected but recoverable (retry, fallback used)
- **error**: Error that needs attention (failed payment, DB connection lost)

---

## 8. Code Style & Readability

### Naming
Clear, searchable names.

```js
// Bad
const x = users.filter(u => u.a > 18);
const fn = (o) => o.t * o.p;

// Good
const adults = users.filter(user => user.age > 18);
const calculateTotal = (order) => order.total * order.quantity;
```

### Function Length
Keep functions small (≤50 lines).

```js
// Bad — 100+ lines
async function processOrder(req, res) {
  // validation
  // calculation
  // database operations
  // email sending
  // response
}

// Good — split into smaller functions
async function processOrder(req, res) {
  const validated = validateOrderInput(req.body);
  const order = await orderService.create(validated);
  await emailService.sendConfirmation(order);
  res.json({ success: true, data: order });
}
```

### Comments
Explain *why*, not *what*.

```js
// Bad
// Increment counter
count++;

// Good
// Retry payment because gateway occasionally returns stale transaction status
await retryPayment(order);
```

---

## 9. Common Anti-Patterns to Flag

| Anti-Pattern | Issue | Fix |
|---|---|---|
| Silent error swallowing | `try { ... } catch (e) { }` | Log and re-throw or handle explicitly |
| Mixing async patterns | Callbacks + Promises + async/await | Use async/await consistently |
| Hardcoded config | `const url = 'http://...'` | Use environment variables |
| Unbounded queries | `User.find()` without limit | Add pagination or limit |
| Missing null checks | `user.email` when user might be null | Check before use |
| Magic numbers | `if (x > 100)` | Extract to named constant |
| God functions | 200+ line functions | Split into smaller functions |
| Tight coupling | Services instantiate dependencies | Inject dependencies |
| No error context | `throw new Error('Failed')` | Include relevant IDs and state |
| Leftover debug code | `console.log`, `debugger` | Remove before merge |

---

## 10. When to Request Changes

- Security issue (hardcoded secret, missing auth check, SQL injection risk)
- Logic error (wrong calculation, race condition, null dereference)
- Test coverage missing for critical path
- Performance issue (N+1 query, unbounded load, missing index)
- Code violates project standards
- Unclear naming or structure that impacts maintainability

---

## 11. When to Approve with Comments

- Minor style inconsistency (can be auto-formatted)
- Suggestion for future refactor (not blocking)
- Nice-to-have optimization (not critical)
- Clarifying comment would help (but code is correct)

---

## 12. Review Tone

- Be respectful and assume good intent
- Explain *why* a change is needed, not just *what*
- Offer suggestions, not demands
- Praise good patterns and improvements
- Keep feedback focused and actionable

