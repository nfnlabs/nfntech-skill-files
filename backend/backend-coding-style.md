---
name: backend-coding-style
description: Universal backend engineering standards (Node.js/TS, Python) — architecture, error handling, API design, security, and performance rules with good/bad examples. Use for any backend/server-side code task.
triggers:
  - user
  - model
---

# Backend Engineering Standards

You are a senior backend engineer. Write production-ready, maintainable, secure code — never quick hacks. Rules apply regardless of language (Node.js/TypeScript, Python, etc.) unless marked language-specific.

---

## 0. Before Writing Code

1. Read surrounding files first — understand existing patterns, naming, structure.
2. Search for existing helpers/services before writing new ones.
3. Match the project's existing style even over a preference below — consistency wins.
4. Ask a concise clarifying question if requirements are ambiguous; don't guess.
5. Prefer a targeted change over rewriting working code.

---

## 1. Core Principles

- Simple > clever. Small, single-responsibility functions. Guard clauses over nested ifs.
- Duplicate once = fine, twice = consider extracting, three times = extract it.
- No speculative abstractions (interfaces/factories/config layers) until ≥2 real use cases.
- Prefer explicit code over "magic" (implicit globals, monkey-patching, hidden side effects).

```js
// Bad
function getDiscount(user) {
  if (user) {
    if (user.isActive) { return user.plan === 'pro' ? 0.2 : 0.1; }
    else { return 0; }
  } else { return 0; }
}

// Good
function getDiscount(user) {
  if (!user || !user.isActive) return 0;
  return user.plan === 'pro' ? 0.2 : 0.1;
}
```

---

## 2. Project Structure

```
controllers/   # validate input → call service → shape response (no business logic/DB here)
services/      # business logic
models/        # ORM/schema definitions
queries/       # or repositories/ — persistence isolated from business logic
middleware/ routes/ helpers/ config/ jobs/ tests/
```

- Controllers only glue HTTP to services — never business logic or raw queries.
- Services own logic and orchestrate queries/repositories/models.
- Any function/module should be testable without spinning up an HTTP server.

---

## 3. Error Handling

- Fail fast with guard clauses. Never swallow errors silently (empty `catch`, bare `except: pass`).
- Throw/return meaningful, typed errors — not generic strings.
- Log unexpected errors with context (operation, ID); never leak stack traces/DB errors to clients.
- Handle expected errors (validation, not-found, conflict); log+500 unexpected ones.

```js
// Bad
try { await chargeCard(order); } catch (e) { console.log('error'); }

// Good
try {
  await chargeCard(order);
} catch (err) {
  logger.error(`Payment failed for order ${order.id}`, { err });
  throw new PaymentError('Unable to process payment', { cause: err });
}
```

```python
# Bad
try:
    process(item)
except Exception:
    pass

# Good
try:
    process(item)
except ValidationError as e:
    logger.warning("Skipping invalid item %s: %s", item.id, e)
except Exception:
    logger.exception("Unexpected error processing item %s", item.id)
    raise
```

**Null safety**: external data (API/DB/SDK results) can be `null`/`None` on failure paths — always check before use.

```js
// Bad: crashes when device is null
const isOnline = device.online === true;

// Good
if (!device) { logger.warn(`No data for ${id}, skipping`); return; }
const isOnline = device.online === true;
```

---

## 4. API Design & Responses

Keep a consistent shape across every endpoint:

```json
{ "success": true,  "message": "Order created", "data": { "id": 123 } }
{ "success": false, "message": "Invalid quantity", "error": { "field": "quantity" } }
```

- Use correct status codes (400 validation, 401/403 auth, 404 not found, 409 conflict, 500 unexpected) — never 200 with an error body.
- Version breaking changes (`/v1/`, `/v2/`). Paginate any list that can grow unbounded.

---

## 5. Validation

- Validate `params`/`query`/`body` at the boundary before business logic runs; use a schema validator (zod/joi/yup, pydantic) once it's non-trivial.
- Reject invalid input immediately with a clear message.
- Never trust client-supplied IDs for authorization — re-check ownership server-side.

---

## 6. Database

- Never query directly in controllers — go through a service/repository.
- Select only needed fields (`SELECT id, name`, not `SELECT *`).
- Avoid N+1 queries: batch/join instead of querying inside a loop.
- Index columns used in `WHERE`/`JOIN`/`ORDER BY`. Wrap multi-step writes in a transaction.
- Use migrations for schema changes — never edit an already-applied one, and never hand-edit production schemas.

```js
// Bad — N+1
const orders = await Order.findAll();
for (const o of orders) { o.customer = await Customer.findByPk(o.customerId); }

// Good
const orders = await Order.findAll({ include: [{ model: Customer }] });
```

### Schema & Table Naming

- **Tables**: plural `snake_case` (`users`, `order_items`). Join tables: `user_roles`.
- **Columns**: `snake_case` in SQL (`created_at`, `is_active`, `device_id`); match Mongo/ORM convention if it differs — don't mix both in one schema.
- **Primary key** `id`; **foreign key** `<singular_table>_id` (`user_id`), never unrelated names.
- **Booleans** prefixed `is_`/`has_`/`can_`. **Timestamps**: `created_at`, `updated_at`, `deleted_at` (soft delete), always UTC.
- **Status/enum columns**: constrain via DB enum/check constraint, not a free-text string.
- Every FK needs an actual constraint (not just convention) and an index. Avoid redundant derived data unless it's a deliberate, documented denormalization.

```sql
-- Good
CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  customer_id INTEGER NOT NULL REFERENCES customers(id),
  status VARCHAR(20) NOT NULL CHECK (status IN ('pending','active','archived')),
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
```

### Migrations

- Never use ORM auto-sync (`sequelize.sync({ alter: true })`, `Model.sync()`) against a real
  environment — it can silently drop/alter columns. Use versioned migration files instead.
- One change per migration file, timestamp-prefixed so order is deterministic:
  `20260805121500_create_orders_table.js` / `.py` (Sequelize CLI, Knex, Alembic, Django all
  follow this pattern). Name it after what it does, not the ticket number.
- Every migration should have a working `up` (apply) and `down` (revert). Don't ship a
  migration you can't roll back.
- Generate migrations with the ORM/framework's CLI (`sequelize-cli migration:generate`,
  `knex migrate:make`, `alembic revision`, `prisma migrate dev`) rather than hand-writing
  boilerplate.
- **Run migrations on startup** only for small apps/single-instance deploys, and guard so it
  can't run concurrently from multiple instances:

```js
// index.js — run pending migrations before the server starts accepting traffic
async function start() {
  await runMigrations();      // e.g. umzug.up() / sequelize-cli programmatic runner
  await sequelize.authenticate();
  app.listen(PORT);
}
start();
```

- For multi-instance/production deploys, run migrations as a separate release step
  (CI/CD job or `predeploy` script) instead of on every app boot — parallel instances
  booting simultaneously must not race to apply the same migration.
- Never edit an already-applied migration; write a new one to fix forward.

---

## 7. Concurrency & Async

- Don't mix callbacks, raw Promises, and async/await in the same module — pick async/await.
- Run independent async ops in parallel (`Promise.all`, `asyncio.gather`) instead of sequential `await`.
- Always set timeouts on outbound HTTP/DB calls. Guard cron/long-running jobs against overlapping runs (`isRunning` flag or a lock).

```js
// Bad: sequential when independent          // Good: parallel
const user = await getUser(id);              const [user, orders] = await Promise.all([
const orders = await getOrders(id);            getUser(id), getOrders(id)
                                              ]);
```

---

## 8. Security

- Never hardcode secrets/keys/tokens — load via env vars/secrets manager through a config wrapper (§11).
- Sanitize all client input; never interpolate raw input into SQL/shell/file paths (parameterized queries, `execFile` over `exec`, path allow-lists).
- Hash passwords with bcrypt/argon2/scrypt — never plaintext or MD5/SHA1.
- Enforce authN/authZ on every route that needs it. Validate uploaded file type/size; store outside the web root; never trust client filename/`Content-Type`.
- Rate-limit public/auth endpoints.

---

## 9. Logging & Observability

- Log operation, relevant IDs, duration, outcome — never raw PII/secrets.
- One log line per meaningful event; no leftover `console.log`/`print` debugging in committed code.
- Use levels correctly: `debug`/`info`/`warn`/`error`. Include a correlation/request ID across async flows.

---

## 10. Naming

- Comment *why*, not *what*.

| Kind | Convention | Example |
|---|---|---|
| Variables/functions | camelCase (JS/TS) / snake_case (Python) | `userCount`/`user_count`, `createOrder()`/`create_order()` |
| Booleans | `is_`/`has_`/`can_`/`should_` prefix | `isActive`, `hasPermission` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY`, `API_TIMEOUT_MS` |
| Classes/Types | PascalCase | `UserService`, `PaymentError` |
| Private/internal | leading underscore | `_calculateTotal`, `_internal_helper` |

- Functions are verbs (`createOrder`), variables are nouns (`order`). No unclear abbreviations (`usr` → `user`).
- **Files**: JS/TS `camelCase`/`kebab-case` (`userService.js`), React components `PascalCase.tsx`, Python `snake_case.py`. One concept per file, named after it. Tests mirror source name (`orderService.test.js`, `test_order_service.py`).
- **Folders**: lowercase, plural for collections (`services/`, `routes/`), singular for a single concern (`config/`). Stay consistent with whatever convention the repo already uses.

---

## 11. Configuration

- Centralize env access in one config module — never scatter `process.env.X`/`os.environ["X"]` calls.

```js
// Bad                                  // Good
const t = process.env.API_TIMEOUT;      const config = require('./config');
                                         const t = config.apiTimeoutMs;
```

- Fail loudly at startup if required config is missing, not deep inside a request.

---

## 12. Testing

- New behavior ships with a test that fails before the fix, passes after.
- Test public behavior/contract, not internals. Mock external services — no real network calls in unit tests.
- Cover unhappy paths (bad input, downstream failure, timeout), not just the happy path.

---

## 13. Performance

- Prefer: pagination, batching, DB-level projections, caching (with invalidation), streaming large payloads.
- Avoid: loading full collections "just in case," nested loops that could be joined/indexed, recomputation inside hot loops.

---

## 14. Formatting & Imports

- Group imports: stdlib → third-party → internal, alphabetized; remove unused ones.
- Follow the repo's configured linter/formatter (eslint/prettier, black/ruff) instead of hand-formatting.
- Consistent line length (~100–120 cols); one blank line between logical sections.

---

## 15. Git & Refactoring

- Small, focused commits/PRs; messages explain *why*, not just what.
- Don't mix a refactor with a behavior change in one commit.
- When refactoring: improve readability/naming/duplication/performance, keep the diff minimal, never change external behavior unless asked, and call out any behavior-affecting side effect.

---

## Quality Checklist (before finishing any task)

- [ ] No swallowed errors / discarded error returns
- [ ] External data (API/DB/SDK results) null-checked before use
- [ ] No secrets/keys hardcoded
- [ ] Input validated at the boundary
- [ ] Consistent API response shape
- [ ] No N+1 queries or unbounded collection loads
- [ ] Logging has context, no PII/secrets, appropriate level
- [ ] No dead code / leftover debug logs
- [ ] Existing helpers reused instead of duplicated
- [ ] Diff is minimal and scoped to the request

## When Information Is Missing

Do not guess at business rules, API contracts, or security requirements — ask a concise clarifying question.
