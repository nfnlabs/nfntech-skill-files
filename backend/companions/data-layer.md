---
name: data-layer
description: Backend data layer — schema and migrations, naming conventions, query patterns, N+1 avoidance, indexing, transactions, and connection pooling. Read when adding a model/table, writing a migration, or reviewing a diff that touches queries.
---

# Data layer

> Every schema change goes through a migration, checked into version control. Never hand-edit
> a production schema, and never edit a migration that's already been applied.

Business logic that calls into this layer → `architecture.md`. Deployment-time connection
tuning → `performance-deployment.md`.

## 1 · Signals to read before deciding

| Check | Where | What it settles |
|---|---|---|
| ORM/query builder | `package.json`/`requirements.txt` (Sequelize, Prisma, SQLAlchemy, ActiveRecord…) | migration CLI and query idiom to use |
| Migration convention | `migrations/`, `db/migrate/`, `alembic/versions/` | naming, up/down pattern already in use |
| Naming convention | existing table/column names | snake_case vs whatever the ORM already uses — don't mix both in one schema |
| Pooling config | wherever the DB client is constructed | current pool size and timeouts |

## 2 · Naming conventions

- **Tables**: plural `snake_case` (`users`, `order_items`). Join tables: `user_roles`.
- **Columns**: `snake_case` in SQL (`created_at`, `is_active`, `device_id`); match the
  Mongo/ORM convention if it differs from SQL — don't mix both in one schema.
- **Primary key** `id`; **foreign key** `<singular_table>_id` (`user_id`) — never an unrelated
  name.
- **Booleans** prefixed `is_`/`has_`/`can_`. **Timestamps** `created_at`, `updated_at`,
  `deleted_at` (soft delete) — always UTC.
- **Status/enum columns**: constrain via a DB enum or check constraint, not a free-text string.
- Every foreign key needs an actual DB constraint (not just convention) and an index. Avoid
  redundant derived data unless it's a deliberate, documented denormalization.

```sql
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

## 3 · Migrations

- Never use ORM auto-sync (`sequelize.sync({ alter: true })`, `Model.sync()`) against a real
  environment — it can silently drop or alter columns. Use versioned migration files.
- One change per migration file, timestamp-prefixed so order is deterministic
  (`20260805121500_create_orders_table.js`). Name it after what it does, not the ticket number.
- Every migration needs a working `up` (apply) **and** `down` (revert). Don't ship one you
  can't roll back.
- Generate migrations with the ORM/framework's CLI (`sequelize-cli migration:generate`,
  `knex migrate:make`, `alembic revision`, `prisma migrate dev`, `rails g migration`) rather
  than hand-writing boilerplate.
- Never edit an already-applied migration — write a new one to fix forward.
- Run migrations on startup only for small apps/single-instance deploys, guarded so it can't
  run concurrently from multiple instances. For multi-instance/production deploys, run
  migrations as a separate release step (CI/CD job or `predeploy` script) — parallel instances
  booting simultaneously must not race to apply the same migration.

```js
// index.js — small/single-instance: run pending migrations before accepting traffic
async function start() {
  await runMigrations();
  await sequelize.authenticate();
  app.listen(PORT);
}
```

## 4 · Queries

- Never query the database directly from a controller — go through a service/repository.
- Select only needed fields (`SELECT id, name`, not `SELECT *`).
- Watch for N+1 queries: eager-load/`select_related`/`includes`/`JOIN` known access patterns
  instead of looping and querying per item.

```js
// Bad — N+1
const orders = await Order.findAll();
for (const o of orders) { o.customer = await Customer.findByPk(o.customerId); }

// Good
const orders = await Order.findAll({ include: [{ model: Customer }] });
```

- Add indexes for every column used in a `WHERE`, `JOIN`, or `ORDER BY` on tables expected to
  grow. Don't add indexes speculatively on columns that aren't queried.
- Wrap multi-step writes that must succeed or fail together in a database transaction. Don't
  assume application-level retries make up for a missing transactional boundary.
- Set a `NOT NULL` + appropriate default/constraint at the DB level for invariants that must
  always hold — don't rely on application code alone to guarantee data integrity.
- Never build queries by string-formatting values into SQL, even for "trusted" internal
  values — always use bound/parameterized queries.
- Use connection pooling; never open a new raw connection per request.

## 5 · Failure modes

| Symptom | Root cause | Correct fix |
|---|---|---|
| Loop querying per item | N+1 | eager-load / join |
| Query slows down as a table grows | missing index on a `WHERE`/`JOIN`/`ORDER BY` column | add a targeted index |
| Partial write left the DB inconsistent | multi-step write not wrapped in a transaction | wrap in a transaction |
| Two app instances both try to run the same migration | migrations run on boot in a multi-instance deploy | move migrations to a separate release step |
| Columns silently dropped after a deploy | ORM auto-sync used against a real environment | versioned migrations only |
| A migration can't be reverted | shipped without a `down` | always write both directions |
| Duplicate/invalid data slips in | invariant enforced only in application code | add a DB-level constraint |

## 6 · Done when

- Schema change has a migration with both `up` and `down`, generated via the framework CLI
- New/changed foreign keys have both a constraint and an index
- No query loops per item where a join/eager-load would do
- Multi-step writes are transactional
- No raw string interpolation into a query
