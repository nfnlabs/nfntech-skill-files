---
name: architecture
description: Backend code placement and API design — routing/controller/service layering, REST conventions, status codes, response shape, versioning, pagination, and per-framework idioms. Read when adding an endpoint, moving logic between layers, or reviewing a diff for layering violations.
---

# Architecture

> A route handler orchestrates — parse input, call a service, shape a response — and never
> contains business logic itself.

Project bootstrap and config → `foundation.md`. Schema and queries → `data-layer.md`.
Validation and authZ → `security.md`.

## 1 · Layering

Separate concerns into: **routing/controllers** (HTTP-in/HTTP-out) → **service/business
logic** (framework-agnostic) → **data access** (DB/cache/external APIs). Business logic must
not import framework request/response objects directly — that's what keeps it testable and
portable without spinning up an HTTP server.

```js
// Bad — mixes validation, business logic, and persistence in the controller
async function createOrder(req, res) {
  if (!req.body.items || req.body.items.length === 0) {
    return res.status(400).json({ error: 'No items' });
  }
  const total = req.body.items.reduce((sum, item) => sum + item.price * item.qty, 0);
  const order = new Order({ items: req.body.items, total });
  await order.save();
  res.json({ success: true, data: order });
}

// Good — controller glues HTTP to service; service owns logic
async function createOrder(req, res) {
  const order = await orderService.create(req.body.items);
  res.json({ success: true, data: order });
}

async function create(items) {
  validateItems(items);
  const total = calculateTotal(items);
  return await orderRepository.create({ items, total });
}
```

Any function/module should be testable without spinning up an HTTP server. Avoid tight
coupling — inject dependencies (db client, logger) rather than instantiating them inside a
service.

## 2 · Placement resolution

Ask in order, stop at the first yes:

1. Parses/validates an HTTP request or shapes a response? → **controller/route**
2. Coordinates business rules, orchestrates one or more data calls? → **service**
3. Reads/writes the database, cache, or an external API? → **data access / repository**
4. Used the same way by two or more services? → promote to a shared helper, named after what
   it does, not "utils"

## 3 · API design

- Consistent, predictable resource naming (`/users/{id}/orders`, plural nouns, no verbs in
  REST paths). For RPC-style or GraphQL, be consistent with that convention instead.
- Version the API from day one (`/v1/...`, header-based, or media-type versioning) — never
  ship an unversioned public API you intend to change.
- Return correct HTTP status codes — don't return `200` with an error payload:

| Code | Meaning |
|---|---|
| 200 / 201 / 204 | success / created / no content |
| 400 / 422 | bad request or validation error / semantic validation error |
| 401 / 403 | unauthenticated / unauthorized |
| 404 / 409 | not found / conflict |
| 429 | rate limited |
| 500 | unhandled server error |

- One consistent response shape across the entire API — two endpoints must never disagree on
  error shape:

```json
{ "success": true,  "message": "Order created", "data": { "id": 123 } }
{ "success": false, "message": "Invalid quantity", "error": { "field": "quantity" } }
```

- Paginate any endpoint that can return an unbounded list. Cursor-based for large/real-time
  datasets, offset-based for small/stable ones. Always cap page size server-side.
- Make endpoints idempotent where the HTTP method implies it (`PUT`, `DELETE`). For
  non-idempotent creates from unreliable clients, support an idempotency key.
- Document every endpoint (OpenAPI/Swagger or the framework-native equivalent) as part of
  writing it, not as an afterthought.

## 4 · Framework-specific idioms

Apply the layering and API-design rules above first; use these only for the syntax/idiom of
the specific framework.

| Framework | Idiom |
|---|---|
| FastAPI | Pydantic models for every request/response schema — validation for free, never a raw `dict`/`Request.json()`. `Depends()` for auth, DB sessions, shared logic instead of repeating it per route. |
| Django | DRF serializers (or Ninja/Pydantic) for validation, not hand-parsed `request.POST`/`request.body`. Django's built-in CSRF/auth/permission framework rather than reimplementing it. |
| Flask | An extension (Flask-Pydantic, Marshmallow, Flask-WTF) for validation — Flask itself does none of this. `flask-limiter` for rate limiting, `flask-talisman` for security headers. |
| Express | A schema validator (Zod, Joi, express-validator) as middleware on every route — Express does no validation itself. `helmet` for security headers, `cors` with an explicit origin allowlist. |
| Rails | Strong parameters on every controller action; never mass-assign raw `params`. |
| Any other (Go/Gin, Java/Spring…) | Find that framework's idiomatic equivalent for input validation, centralized error handling, DI for shared resources, and auth/CORS/rate-limit/logging middleware — nearly every framework has a "right way." Use it instead of reimplementing it. |

## 5 · Failure modes

| Symptom in the diff | Why it matters | Correct move |
|---|---|---|
| Controller queries the DB directly | bypasses the service layer; untestable without HTTP | route through a service/repository |
| Business logic imports `req`/`res` | can't unit test without mocking HTTP | pass plain values into the service |
| Two endpoints return different error shapes | clients can't handle errors generically | centralize the response shape |
| Endpoint returns `200` with `{error: ...}` | breaks HTTP semantics and client error handling | return the correct status code |
| Unversioned public endpoint | any future change is a breaking change | version from day one |
| List endpoint with no limit | unbounded response size and DB load | paginate, cap page size server-side |

## 6 · Done when

- Controller/route contains no business logic or raw queries
- Every endpoint validated, documented, and returns the shared response shape
- Correct status codes used; no `200` with an error body
- Unbounded lists are paginated with a server-side cap
- New/changed endpoints match an existing reference endpoint's conventions, or the deviation
  is called out
