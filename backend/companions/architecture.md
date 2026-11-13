---
name: architecture
description: Backend code placement and API design — layering, REST conventions, status codes, response shape, pagination, versioning, and per-framework idioms. Read when adding an endpoint, moving logic between layers, or reviewing layering.
---

# Architecture

> A route handler orchestrates: parse input, call a service, shape the response. It holds
> no business logic.

Bootstrap → `foundation.md`. Queries → `data-layer.md`. Validation and authZ → `security.md`.

## 1 · Layering

Routes and controllers (HTTP in and out) → services (business logic, framework-agnostic) →
data access (DB, cache, external APIs). Services never import request or response objects.
Inject dependencies (DB client, logger) through the constructor, so services are testable
without an HTTP server.

```js
// Bad: validation, logic and persistence in the controller
async function createOrder(req, res) {
  if (!req.body.items?.length) return res.status(400).json({ error: 'No items' });
  const total = req.body.items.reduce((s, i) => s + i.price * i.qty, 0);
  res.json({ success: true, data: await new Order({ items: req.body.items, total }).save() });
}

// Good
async function createOrder(req, res) {
  res.json({ success: true, data: await orderService.create(req.body.items) });
}
```

Placement: if it parses HTTP or shapes a response, it's a controller. If it coordinates
business rules, it's a service. If it touches the DB, cache or an external API, it's data
access. A helper shared by two or more services gets a name that says what it does, not `utils`.

## 2 · API design

- Plural nouns, no verbs in REST paths (`/users/{id}/orders`). Stay consistent in RPC or GraphQL.
- Version from day one (`/v1/`, header or media type).
- Use correct status codes. Never return `200` with an error body.

| Code | Meaning |
|---|---|
| 200 / 201 / 204 | success / created / no content |
| 400 / 422 | malformed request / validation error |
| 401 / 403 | unauthenticated / unauthorized |
| 404 / 409 | not found / conflict |
| 429 | rate limited |
| 500 | unhandled server error |

- One response shape for the whole API. Two endpoints must never disagree on error structure:

```json
{ "success": true,  "message": "Order created", "data": { "id": 123 } }
{ "success": false, "message": "Invalid quantity", "error": { "field": "quantity" } }
```

- Paginate every list that can grow. Use cursors for large or real-time data and offsets for small, stable data. Cap page size server-side.
- `PUT` and `DELETE` are idempotent. Non-idempotent creates from unreliable clients take an idempotency key.
- Document each endpoint (OpenAPI or the framework's equivalent) when you write it.

## 3 · Framework idioms

Apply the rules above first. This table covers only syntax and idiom.

| Framework | Structure | Validation and security idiom |
|---|---|---|
| Express | `express.Router()` per domain, mounted in the app | Zod, Joi or express-validator middleware on every route; `helmet`; `cors` with an origin allowlist |
| FastAPI | `APIRouter` per domain; `async def` only for real async I/O, plain `def` for sync or CPU-bound work | Pydantic models for every request and response; `Depends()` for auth and DB sessions |
| Django | One app per domain with a `services.py`; thin views and models | DRF serializers (or Ninja/Pydantic); built-in CSRF, auth and permissions |
| Flask | Blueprints per domain | Flask-Pydantic, Marshmallow or Flask-WTF; `flask-limiter`; `flask-talisman` |
| Rails | Thin controllers; logic in models, service objects or concerns | Strong parameters on every action; never mass-assign raw `params` |
| Other (Go, Spring…) | The framework's idiomatic structure | Its built-in validation, error handling, DI and middleware, not reimplementations |

## 4 · Done when

- Controllers contain no business logic and no raw queries
- Every endpoint is validated, documented and returns the shared response shape
- Status codes are correct; unbounded lists are paginated with a server-side cap
- New endpoints match a reference endpoint, or the deviation is called out
