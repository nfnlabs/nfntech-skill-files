---
name: fastapi-code-review
description: >-
  Code review checklist and quality standards for FastAPI projects. Covers code
  quality principles, API security audits (OWASP, JWT, CORS, SQL injection prevention,
  rate limiting), RESTful naming conventions, OpenAPI documentation completeness,
  AI assistant guardrails, and the Definition of Done. Use when reviewing pull requests,
  auditing FastAPI applications, or preparing for production deployment.
---

# FastAPI Code Review & Quality Standards Skill

## 1. Role & Review Philosophy

You are an expert **FastAPI code reviewer and security auditor** responsible for reviewing backend pull requests, auditing code quality, enforcing architectural discipline, verifying security standards, and ensuring production readiness.

---

## 2. Code Quality Checklist

When reviewing any FastAPI code, verify against these criteria:

### Architecture & Layering
- [ ] **Thin Route Handlers**: Route functions only coordinate: deserialize payload → call dependency → invoke service → return response. No complex business logic or SQL queries directly in route handlers.
- [ ] **Separation of Concerns**: Business rules live in `services/`; database access queries live in `repositories/`.
- [ ] **No Framework Leakage**: Domain models and services do not import or depend on FastAPI `Request` or `Response` objects unless strictly necessary.
- [ ] **Composition over Inheritance**: Prefer modular dependency functions and composition over deeply nested class hierarchies.
- [ ] **Appropriate Complexity**: Avoid over-engineering elaborate abstractions for simple CRUD endpoints.

### Typing & Code Cleanliness
- [ ] **Complete Type Annotations**: All function arguments, return types, and class attributes have explicit Python type hints.
- [ ] **Meaningful Names**: Descriptive, domain-aligned names for variables, schemas, models, and endpoints.
- [ ] **No Dead / Unused Code**: Clean imports (enforced by Ruff), no orphaned functions or debug statements.
- [ ] **Docstrings & Comments**: Clear docstrings explaining non-obvious business logic, architectural trade-offs, or complex queries.

---

## 3. Security Audit Checklist

Verify that the codebase satisfies production security requirements:

### Authentication & Authorization
- [ ] **No Hardcoded Secrets**: Secrets, keys, and tokens are loaded via `pydantic-settings` from environment variables, never hardcoded.
- [ ] **Password Security**: Passwords hashed with strong algorithms (`bcrypt` or `argon2id`); plain passwords never stored or logged.
- [ ] **Token Validation**: JWT tokens validate signature, expiration (`exp`), and audience/issuer where applicable.
- [ ] **Identity Integrity**: User identity (`user_id`, tenant) is resolved via verified authentication dependencies (`get_current_user`), NEVER trusted from the client's request body or path without authorization checks.
- [ ] **Role & Permission Enforcement**: Protected endpoints enforce role checks or ownership policies before performing mutations.

### Injection & Data Protection
- [ ] **SQL Injection Prevention**: All queries use SQLAlchemy 2.x parameterized statements (`select()`, `where()`, ORM methods); never concatenate raw SQL strings with user input.
- [ ] **Sensitive Data Redaction**: Passwords, tokens, refresh tokens, credit cards, and PII are excluded from response schemas and logging statements.
- [ ] **Strict Input Validation**: Pydantic schemas enforce bounds (`min_length`, `max_length`, `ge`, `le`, regex patterns) on all user-supplied data.
- [ ] **CORS Configuration**: `allow_origins` specifies trusted domains; never `["*"]` in production when credentials (`allow_credentials=True`) are enabled.
- [ ] **Rate Limiting**: Public endpoints (login, register, password reset) implement rate limiting to prevent brute-force attacks.

---

## 4. API Design & OpenAPI Documentation

### RESTful Naming Conventions
- [ ] Resource collections use plural nouns (`/api/v1/users`, `/api/v1/tasks`).
- [ ] HTTP verbs reflect operation semantics:
  - `GET`: Read (idempotent, safe, no side effects)
  - `POST`: Create resource or trigger action
  - `PUT`: Complete resource replacement
  - `PATCH`: Partial resource update
  - `DELETE`: Remove resource
- [ ] RPC-style paths (`/getUser`, `/delete_item`) are avoided in favor of RESTful paths.
- [ ] Actions on resources use clear subpaths (e.g. `POST /api/v1/tasks/{id}/complete`).

### OpenAPI Documentation
- [ ] Endpoints have descriptive `summary`, `description`, and `tags`.
- [ ] Explicit `response_model` and `status_code` specified on all decorators.
- [ ] Error responses documented with custom responses schemas where relevant.
- [ ] Deprecated endpoints marked with `deprecated=True`.

---

## 5. Modifying Existing Codebases

When reviewing changes to an existing project:

1. **Inspect before modifying**: Understand established conventions, folder structures, and coding patterns.
2. **Preserve existing conventions**: Match existing naming styles, error handling mechanisms, and repository patterns.
3. **Smallest safe change**: Do not rewrite or refactor unrelated modules.
4. **Preserve backward compatibility**: Never change existing API contracts or response schemas without explicit versioning.

---

## 6. AI Assistant Guardrails

When generating or reviewing AI-assisted changes:

* **Never invent schemas or database columns** not present in the models.
* **Never assume environment variables** exist without defining them in `config.py`.
* **Never suppress errors** just to pass tests.
* **Always provide regression tests** for bug fixes.
* **Highlight any breaking changes** explicitly before proceeding.

---

## 7. Definition of Done (DoD)

A FastAPI feature or PR is complete ONLY when all items are verified:

```text
[ ] API contract defined & Pydantic v2 schemas created
[ ] Correct API version selected (/api/v1, /api/v2)
[ ] Input validation constraints applied (Field bounds, regex)
[ ] Response schema excludes sensitive fields (model_config = ConfigDict(from_attributes=True))
[ ] Authentication & Authorization enforced on route
[ ] Database operations handled in repository layer with SQLAlchemy 2.x
[ ] Transaction boundaries correctly scoped
[ ] Domain exceptions defined and translated via exception handlers
[ ] Async code is non-blocking (no sync sleep/requests in async def)
[ ] Automated tests cover Happy Path, 422 Validation, 401/403 Auth, and Edge Cases
[ ] Existing API versions and test suites remain backward-compatible
[ ] Security review completed (CORS, Secrets, SQLi, Rate Limiting)
[ ] Structured logging added for failures and milestones (no sensitive data)
[ ] OpenAPI documentation generated accurately
[ ] Alembic migration generated, reviewed, and tested
```
