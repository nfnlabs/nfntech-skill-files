---
name: foundation
description: Backend project bootstrap — entry point, folder layout, configuration and environment loading, and concurrency/async basics. Read when starting a new service, joining one for the first time, or wiring up config.
---

# Foundation

> One entry point, one config module, no ad hoc `process.env`/`os.environ` reads scattered
> through business code.

API/route conventions → `architecture.md`. Schema and queries → `data-layer.md`. Secrets and
input handling → `security.md`.

## 1 · Signals to read before deciding

| Check | Where | What it settles |
|---|---|---|
| Stack and majors | `package.json`, `pyproject.toml`, `Gemfile`, `go.mod` | which framework idioms apply |
| Entry point | `main.py`, `app.py`, `server.js`, `manage.py` | how the app boots today |
| Config pattern | grep `process.env.`/`os.environ[` count vs a single `config/` module | centralized or scattered |
| Required env vars | `.env.example` | the documented config surface |
| Binding conventions | `CLAUDE.md`, `AGENTS.md`, `.cursorrules` | rules that outrank this skill |

An existing pattern wins. Match it, say so in one line, and don't convert working code as a
side effect — that's a separate agreed task.

## 2 · Project structure

Small projects can stay flat; group by domain/feature (`users/`, `orders/`) over generic
technical buckets once the project grows past a handful of routes. Keep a single source of
truth for configuration, one for routing, one for the data models/schema — don't duplicate
route or model definitions across layers.

```
controllers/   # or routes/ — validate input → call service → shape response, no logic/DB here
services/      # business logic, framework-agnostic, no request/response objects
models/        # ORM/schema definitions
queries/       # or repositories/ — persistence isolated from business logic
middleware/ helpers/ config/ jobs/ tests/
```

`utils`/`helpers` files are a smell once they exceed a few functions — split by what the
functions actually do. One clear entry point; avoid circular imports between routing and
business-logic modules.

## 3 · Configuration

Centralize env access in one config module, validated at startup — fail loudly and
immediately if a required var is missing, not deep inside a request.

```js
// Bad                                  // Good
const t = process.env.API_TIMEOUT;      const config = require('./config');
                                         const t = config.apiTimeoutMs;
```

Keep environment parity: dev/staging/prod run the same code path, differing only by config
values — not by `if env == "prod"` logic sprinkled through business code. Never commit
environment-specific secrets, including in test fixtures or seed scripts (`security.md`
covers secrets handling in depth).

## 4 · Concurrency & async

- Pick one async style and hold the line — don't mix callbacks, raw Promises, and
  async/await in the same module.
- Run independent async operations in parallel (`Promise.all`, `asyncio.gather`) instead of
  sequential `await`.
- Don't block the event loop / worker thread with synchronous I/O in an async framework (a
  blocking `requests` call inside `async def`, a blocking DB driver in Node) — use the
  async-native client or offload to a thread/worker pool.
- Guard shared mutable state accessed by concurrent requests/workers with locking, or better,
  avoid it — keep handlers stateless and push shared state into the database/cache.
- Push slow or non-critical-path work (emails, webhooks, report generation) to a background
  job/queue (Celery, Sidekiq, BullMQ) instead of doing it inline in the request/response cycle.
- Guard cron/long-running jobs against overlapping runs (`isRunning` flag or a lock).
- Set timeouts on every outbound call (DB, HTTP, cache) — an unbounded call can exhaust the
  connection pool for the whole service.

```js
// Bad: sequential when independent          // Good: parallel
const user = await getUser(id);              const [user, orders] = await Promise.all([
const orders = await getOrders(id);            getUser(id), getOrders(id)
                                              ]);
```

## 5 · Framework bootstrap notes

| Framework | Notes |
|---|---|
| FastAPI | `APIRouter` per domain, included into the main app — avoids one giant `main.py`. Use `async def` only for actually-async I/O; plain `def` for CPU-bound/sync routes so FastAPI runs them in a thread pool. |
| Django | One app per domain; keep business logic out of views and fat `models.py` methods — a `services.py` per app keeps it testable. |
| Flask | Blueprints per domain instead of one `app.py` with every route. |
| Express | Router per domain (`express.Router()`), mounted in the main app. |
| Rails | Controllers stay thin — push logic into models, service objects, or concerns. |

## 6 · Style, naming and git

- Simple > clever. Small, single-responsibility functions (Node convention: ≤50 lines);
  guard clauses over nested `if`s. Duplicate logic once is fine, twice consider extracting,
  three times extract it — no speculative abstractions before there are ≥2 real use cases.
- Comment *why*, not *what* — a comment restating the code is worse than no comment.

| Kind | Convention | Example |
|---|---|---|
| Variables/functions | camelCase (JS/TS) / snake_case (Python) | `userCount`, `createOrder()` |
| Booleans | `is_`/`has_`/`can_`/`should_` prefix | `isActive`, `hasPermission` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY`, `API_TIMEOUT_MS` |
| Classes/Types | PascalCase | `UserService`, `PaymentError` |
| Files | camelCase/kebab-case (JS/TS), snake_case (Python) | `userService.js`, `user_service.py` |

Functions are verbs, variables are nouns; no unclear abbreviations (`usr` → `user`). Tests
mirror the source file's name (`orderService.test.js`, `test_order_service.py`). Group
imports stdlib/framework → third-party → internal, alphabetized, unused ones removed. Follow
the repo's configured linter/formatter instead of hand-formatting.

Small, focused commits/PRs; messages explain *why*, not just what. Don't mix a refactor with
a behavior change in the same commit. When refactoring: improve readability/naming/
duplication/performance, keep the diff minimal, never change external behavior unless asked,
and call out any behavior-affecting side effect.

## 7 · Done when

- Single entry point; no circular imports between routing and business logic
- All config read through one module; startup fails loudly if a required var is missing
- No `if env == "prod"` conditionals inside business logic
- Independent async operations run in parallel, not sequentially
- No blocking I/O inside an async handler
- Slow/non-critical work is queued, not inline in the request cycle
