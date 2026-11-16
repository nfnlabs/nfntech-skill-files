---
name: foundation
description: Backend project bootstrap — entry point, folder layout, configuration and environment loading, and async basics. Read when starting a service, joining one, or wiring up config.
---

# Foundation

> One entry point, one config module, no ad hoc `process.env` or `os.environ` reads in
> business code.

Routes → `architecture.md`. Data → `data-layer.md`. Secrets and input → `security.md`.

## 1 · Before deciding

Check `package.json`, `pyproject.toml`, `Gemfile` or `go.mod` for stack and majors, the
entry point (`server.js`, `main.py`, `app.py`, `manage.py`), and `.env.example` for the
config surface. If the project is already set up a certain way, match it and note that in
one line. Don't convert working code as a side effect.

## 2 · Structure

Small projects can stay flat. Past a handful of routes, group by domain (`users/`,
`orders/`), not by generic buckets. Keep one source of truth each for config, routing and
models. Don't duplicate route or model definitions across layers.

```
controllers/   validate input → call service → shape response; no logic or DB
services/      business logic; framework-agnostic
models/        ORM and schema definitions
queries/       persistence (or repositories/), isolated from business logic
middleware/ helpers/ config/ jobs/ tests/
```

A `utils` or `helpers` file with more than a few functions gets split by purpose. Avoid
circular imports between routing and business logic.

## 3 · Configuration

Read env vars in one config module, validated at startup. A missing required variable
must fail immediately, not inside a request.

```js
// Bad                                  // Good
const t = process.env.API_TIMEOUT;      const t = config.apiTimeoutMs; // config.js validates at boot
```

Dev, staging and prod run the same code path and differ only by config values, never by
`if (env === 'prod')` in business logic. Never commit environment-specific secrets,
including in test fixtures or seed scripts.

## 4 · Async and concurrency

- One async style per module: async/await. Don't mix callbacks, raw promises and await.
- Run independent awaits in parallel (`Promise.all`, `asyncio.gather`).
- No blocking I/O inside an async handler. Use an async client or a worker pool.
- Keep handlers stateless. Shared mutable state lives in the database or cache, or behind a lock.
- Move slow or non-critical work (email, webhooks, reports) to a queue (BullMQ, Celery, Sidekiq).
- Guard cron and long-running jobs against overlap with a lock or an `isRunning` flag.

```js
// Bad: sequential when independent          // Good
const user = await getUser(id);              const [user, orders] = await Promise.all([getUser(id), getOrders(id)]);
const orders = await getOrders(id);
```

Timeouts on outbound calls are in `performance-deployment.md` §3.

## 5 · Style, naming and commits

Simple beats clever. Keep functions under about 50 lines. Use guard clauses over nested
`if`s. Tolerate one duplicate, extract at three, and don't add an abstraction before there
are two real use cases. Comment *why*, never *what*.

- Variables and functions: `camelCase` (JS/TS) or `snake_case` (Python). Classes: `PascalCase`. Constants: `UPPER_SNAKE_CASE`. Booleans: `is_`, `has_`, `can_`, `should_`.
- Functions are verbs, variables are nouns. No unclear abbreviations.
- Tests mirror the source name (`orderService.test.js`, `test_order_service.py`).
- Imports: stdlib, framework, third-party, then internal. Alphabetized, unused ones removed.
- Use the repo's linter and formatter. Don't hand-format.
- Small commits. Never mix a refactor with a behavior change. Refactors keep external behavior, and any side effect gets called out.

## 6 · Done when

- One entry point; no circular imports between routing and business logic
- All config read through one module; startup fails if a required variable is missing
- Independent async operations run in parallel; no blocking I/O in an async handler
- Slow or non-critical work is queued, not done inline in the request
