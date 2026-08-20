# Backend Server Coding Rules

Framework-agnostic rules for building server-side APIs and backends (Python:
FastAPI/Django/Flask · Node: Express/NestJS · Ruby: Rails · Go · etc).
Feed this file to an AI assistant as a standing reference before/while it
writes backend code. Rules are written as directives ("Always/Never/Prefer")
so they can be applied mechanically. Framework-specific notes are at the
bottom — everything above them applies regardless of language or framework.

---

## 1. Core Principles

- Optimize for correctness and clarity first, then performance. Don't
  micro-optimize before there's a measured bottleneck.
- Keep functions/handlers small and single-purpose. A route handler should
  orchestrate (parse input → call service/business logic → return response),
  not contain business logic itself.
- Separate concerns into layers: **routing/controllers** (HTTP-in/HTTP-out)
  → **service/business logic** (framework-agnostic) → **data access**
  (DB/cache/external APIs). Business logic must not import framework request/
  response objects directly — this keeps it testable and portable.
- No dead code, no commented-out code, no speculative abstractions for
  hypothetical future requirements. Delete instead of commenting out.
- Fail fast and loud in development; fail safe and quiet (to the client) in
  production. Never leak stack traces, internal paths, or SQL to end users.
- Every side-effecting operation (write, delete, external call) should be
  traceable: log who/what/when at the point it happens, not inferred later.

## 2. Project Structure

- One clear entry point (`main.py`, `app.py`, `server.js`, etc). Avoid
  circular imports between routing and business-logic modules.
- Group code by domain/feature (e.g. `users/`, `orders/`) over generic
  technical buckets (`controllers/`, `models/`, `utils/`) once the project
  grows past a handful of routes. Small projects can stay flat.
- Keep a single source of truth for configuration, one for routing, one for
  the data models/schema. Don't duplicate route definitions or model
  definitions across layers.
- `utils`/`helpers` files are a smell once they exceed a few functions —
  split by what the functions actually do.

## 3. API Design

- Use consistent, predictable resource naming (`/users/{id}/orders`, plural
  nouns, no verbs in REST paths). For RPC-style or GraphQL, be consistent
  with the chosen convention instead.
- Version the API from day one (`/v1/...`, header-based, or media-type
  versioning) — never ship an unversioned public API you intend to change.
- Return correct HTTP status codes: `200` success, `201` created, `204` no
  content, `400` bad request/validation, `401` unauthenticated, `403`
  unauthorized, `404` not found, `409` conflict, `422` semantic validation
  error, `429` rate limited, `500` unhandled server error. Don't return `200`
  with an error payload.
- Use a single consistent error response shape across the entire API, e.g.
  `{ "error": { "code": "...", "message": "...", "details": [...] } }`.
  Never let two endpoints disagree on error shape.
- Validate and coerce **all** external input (body, query params, path
  params, headers, cookies) at the boundary using a schema/type system
  (Pydantic, Zod, JSON Schema, Rails strong params, etc.) — never trust
  client-supplied types or presence.
- Paginate any endpoint that can return an unbounded list. Prefer
  cursor-based pagination for large/real-time datasets, offset pagination
  only for small/stable ones. Always cap page size server-side.
- Make endpoints idempotent where the HTTP method implies it (`PUT`,
  `DELETE`). For non-idempotent creates from unreliable clients, support an
  idempotency key.
- Document every endpoint (OpenAPI/Swagger, or framework-native equivalent)
  as part of writing it, not as an afterthought.

## 4. Security

- Never trust client input. Validate type, length, range, and format on
  every field, server-side, regardless of client-side validation.
- Always use parameterized queries / ORM query builders. Never
  string-concatenate or f-string/template user input into SQL, shell
  commands, or NoSQL queries.
- Hash passwords with a slow, salted algorithm (bcrypt/argon2/scrypt).
  Never store plaintext or reversibly-encrypted passwords. Never roll your
  own crypto.
- Authentication vs authorization are separate checks — verify identity
  first, then explicitly check permission for the specific resource/action
  being accessed (including object-level ownership checks, not just
  role checks — this prevents IDOR bugs).
- Store secrets (API keys, DB credentials, signing keys) in environment
  variables or a secrets manager — never hard-code them, never commit them,
  never log them. Add a `.env.example` with dummy values, keep `.env` in
  `.gitignore`.
- Set security headers by default: `Content-Security-Policy`,
  `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`,
  `X-Frame-Options`/`frame-ancestors`. Use a framework middleware/gem/package
  for this rather than hand-rolling.
- Configure CORS explicitly with an allowlist of origins — never
  `Access-Control-Allow-Origin: *` on an endpoint that accepts credentials.
- Rate-limit authentication endpoints and any expensive/public endpoint.
  Add brute-force lockout or backoff on login/OTP/password-reset flows.
- Escape/encode all output that goes into HTML, and rely on the templating
  engine's autoescaping rather than disabling it. Sanitize (don't just
  block) rich-text/HTML user input if it must be rendered.
- Use CSRF protection for any cookie-authenticated, state-changing endpoint
  reachable from a browser. Not needed for pure token-bearer APIs without
  cookies.
- Keep dependencies patched; run a vulnerability scanner
  (`pip-audit`/`npm audit`/`bundler-audit`/Dependabot/Snyk) in CI, not
  manually and occasionally.
- Enforce HTTPS/TLS in production; redirect HTTP → HTTPS at the edge.
- Set explicit request size limits and timeouts (body size, upload size,
  connection timeout) to bound resource usage per request.

## 5. Error Handling

- Centralize error handling with one global exception handler/middleware
  that maps exceptions to the standard error response shape — don't
  try/catch the same boilerplate in every handler.
- Distinguish operational errors (bad input, not found, conflict — expected,
  return a clean 4xx) from programming errors/bugs (unexpected — log with
  full context, return a generic 500, alert).
- Never swallow exceptions silently (`except: pass` / empty `catch {}`).
  At minimum, log them with context.
- Never expose internal error details, stack traces, or library error
  messages directly to API clients in production. Log the detail internally,
  return a generic safe message externally.
- Use custom/typed exception classes for expected domain errors
  (`NotFoundError`, `ValidationError`, `PermissionDeniedError`) instead of
  raising generic exceptions or returning magic error strings.

## 6. Logging & Observability

- Log in structured format (JSON) in any environment where logs are
  aggregated — not raw string concatenation.
- Include correlation/request IDs on every log line for a request, and
  propagate them through downstream service calls.
- Never log secrets, passwords, tokens, full credit card numbers, or other
  PII/sensitive fields — redact before logging.
- Use log levels correctly: `DEBUG` (dev detail), `INFO` (normal operational
  events), `WARNING` (recoverable/unexpected but handled), `ERROR`
  (needs attention), `CRITICAL` (system is down). Don't log routine
  operations at `ERROR`.
- Expose a health-check endpoint (`/health` or `/healthz`) that checks
  critical dependencies (DB, cache) are reachable, and a separate liveness
  check that doesn't. Expose metrics (request count, latency, error rate)
  for scraping (Prometheus or equivalent) on any service that will run in
  production.

## 7. Data Layer

- Every schema change goes through a migration file, checked into version
  control — never hand-edit the production schema.
- Wrap multi-step writes that must succeed or fail together in a database
  transaction. Don't assume application-level retries make up for missing
  transactional boundaries.
- Watch for N+1 queries: eager-load/`select_related`/`includes`/`JOIN` known
  access patterns instead of looping and querying per item.
- Add indexes for every column used in a `WHERE`, `JOIN`, or `ORDER BY` on
  tables expected to grow. Don't add indexes speculatively on columns that
  aren't queried.
- Use connection pooling; never open a new raw connection per request.
- Set a `NOT NULL` + appropriate default/constraint at the DB level for
  invariants that must always hold — don't rely on application code alone
  to guarantee data integrity.
- Never build queries by string-formatting values into SQL, even for
  "trusted" internal values — always use bound parameters.

## 8. Configuration & Environments

- Config comes from environment variables (or a config service), loaded
  once at startup, validated at startup (fail immediately if a required
  var is missing) — not read ad hoc from `os.environ`/`process.env`
  scattered through the codebase.
- Keep environment parity: dev/staging/prod should run the same code path,
  differing only by config values, not by conditional `if env == "prod"`
  logic sprinkled through business code.
- Never commit environment-specific secrets or credentials, including in
  test fixtures or seed scripts.

## 9. Concurrency & Async

- Don't block the event loop / worker thread with synchronous I/O in an
  async framework (e.g. blocking `requests` call in `async def` FastAPI
  handler, blocking DB driver in Node) — use the async-native client or
  offload to a thread/worker pool.
- Guard shared mutable state accessed by concurrent requests/workers with
  proper locking, or better, avoid shared mutable state — keep handlers
  stateless and push shared state into the database/cache.
- Push slow or non-critical-path work (emails, webhooks, report generation)
  to a background job/queue (Celery, Sidekiq, BullMQ, etc.) instead of
  doing it inline in the request/response cycle.

## 10. Testing

- Every endpoint needs at least: one happy-path test, one validation-failure
  test, one auth-failure test (if protected), one not-found/edge-case test.
- Test business logic independent of the HTTP layer where the architecture
  allows it (unit test the service function, not just the route).
- Use a real (containerized/in-memory) database for integration tests
  rather than mocking the DB — mocked-DB tests can pass while the real
  query is broken.
- Tests must be independent and order-unaffected: no test should depend on
  another test's side effects; reset/seed state per test.
- Run tests, linter, and a dependency/security audit in CI on every change,
  not just locally.

## 11. Performance

- Cache expensive, frequently-read, rarely-changing data (Redis/in-memory)
  with an explicit invalidation strategy — never cache without a plan to
  invalidate it.
- Measure before optimizing: profile or use APM data to find the actual
  bottleneck instead of guessing.
- Stream large responses/file downloads instead of loading the entire
  payload into memory.
- Set sane timeouts on every outbound call (DB, HTTP, cache) — an
  unbounded call can exhaust the connection pool for the whole service.

## 12. Dependency & Version Management

- Pin dependency versions (lockfile: `poetry.lock`/`requirements.txt` with
  hashes, `package-lock.json`, `Gemfile.lock`) so builds are reproducible.
- Prefer well-maintained, widely-used libraries for security-sensitive
  functionality (auth, crypto, serialization) over hand-rolled or
  unmaintained ones.
- Review what a new dependency actually adds before pulling it in for a
  small amount of functionality you could write directly.

## 13. Deployment Readiness

- The app must start from a clean environment using only checked-in config
  templates + documented env vars — no manual, undocumented setup steps.
- Handle graceful shutdown: finish in-flight requests and close DB/queue
  connections cleanly on `SIGTERM` before exiting.
- Never run the framework's debug mode, auto-reload, or verbose error
  pages in production.
- Container images (if used) should run as a non-root user and include
  only what's needed to run the app.

---

## Framework-Specific Notes

These map the rules above onto specific stacks. Apply the general rules
first; use these only for the syntax/idiom of the specific framework.

### Python — FastAPI
- Use Pydantic models for all request/response schemas — get validation
  (§3) for free; don't accept raw `dict`/`Request.json()` where a typed
  model would do.
- Use `Depends()` for auth, DB sessions, and shared logic instead of
  repeating it per route.
- Use `async def` only for actually-async I/O; use plain `def` for
  CPU-bound or sync-library routes so FastAPI runs them in a thread pool
  (see §9).
- Use `APIRouter` per domain/feature, included into the main app — avoids
  one giant `main.py` (see §2).

### Python — Django
- Use Django REST Framework serializers (or Ninja/Pydantic) for API
  validation rather than hand-parsing `request.POST`/`request.body`.
- Keep business logic out of views and out of `models.py` methods when it
  grows complex — a `services.py` per app keeps it testable (see §1).
- Always use the ORM/QuerySet API, not raw SQL, unless there's a measured
  need — and even then, use parameterized `cursor.execute` (see §4, §7).
- Run `makemigrations`/`migrate` for every model change; never edit
  applied migrations after they've shipped to another environment.
- Use Django's built-in CSRF, auth, and permission framework rather than
  reimplementing it.

### Python — Flask
- Use an extension (Flask-Pydantic, Marshmallow, Flask-WTF) for input
  validation — Flask itself does none of this for you (see §3).
- Use Blueprints per domain/feature instead of one `app.py` with every
  route (see §2).
- Use `flask-limiter` for rate limiting and `flask-talisman` (or equivalent)
  for security headers (see §4) rather than hand-rolling.
- Don't use Flask's built-in dev server or `debug=True` in production —
  run behind gunicorn/uvicorn-worker + a reverse proxy.

### Node — Express
- Use a schema validator (Zod, Joi, express-validator) as middleware on
  every route (see §3) — Express does no validation itself.
- Use `helmet` for security headers and `cors` with an explicit origin
  allowlist (see §4).
- Centralize error handling in a single Express error-handling middleware
  (4-arg signature) rather than per-route try/catch blocks (see §5).
- Always call `next(err)` on error in async handlers, or use an async
  wrapper — unhandled promise rejections in route handlers crash silently
  otherwise.

### Ruby — Rails
- Use strong parameters on every controller action (see §3); never mass-
  assign raw `params`.
- Keep controllers thin — push logic into models, service objects, or
  concerns (see §1); a controller action should read as a short script.
- Rely on Rails' built-in CSRF protection, `has_secure_password`
  (bcrypt-based), and ActiveRecord parameterized queries rather than
  bypassing them (see §4).
- Use `ActiveRecord::Base.transaction` for multi-step writes (see §7), and
  `includes`/`eager_load` to avoid N+1 queries.

### General mapping for any other framework (Go/Gin, Java/Spring, etc.)
- Find that framework's idiomatic equivalent for: input validation,
  centralized error handling, dependency injection for shared resources
  (DB/cache clients), and middleware for auth/CORS/rate-limiting/logging —
  the five things nearly every framework provides a "right way" to do.
  Use it instead of reimplementing it.
