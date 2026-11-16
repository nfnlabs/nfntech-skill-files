---
name: backend-engineering
description: Owns server-side/API engineering across languages and frameworks (Node/Express, Python FastAPI/Django/Flask, Rails, and others) — the entry point that reads the existing project, then routes to one companion. Triggers on any backend work — endpoints, services, schema and migrations, auth, payments and credits, webhooks, AI model calls, error handling, logging, caching, deployment, tests, and code review.
---

# Backend engineering

> Read the codebase before advising it, then open one companion. An existing convention
> outranks anything in these files.

## 1 · Route by task

| The task | Open |
|---|---|
| Bootstrap, layout, config and env loading, async basics | `companions/foundation.md` |
| Routes, layering, REST, response shape, framework idioms | `companions/architecture.md` |
| Schema, migrations, queries, transactions, shared values under concurrency | `companions/data-layer.md` |
| AuthN/AuthZ, tokens, tenants, validation, secrets, webhooks, SSRF, uploads, rate-limit policy | `companions/security.md` |
| Errors, logging, health checks | `companions/error-handling-logging.md` |
| Caching, rate-limit mechanics, pooling, PM2, Nginx, deploy readiness | `companions/performance-deployment.md` |
| Tests and CI gates | `companions/testing.md` |
| Payments, credits, subscriptions, refunds, billing webhooks | `companions/payments-billing.md` |
| Anything that calls an AI model or stores its output | `companions/ai-features.md` |
| Reviewing a PR, a diff or a whole codebase | `companions/code-review.md` |

Usually one companion, occasionally two.

## 2 · Read the project first

```sh
cat package.json pyproject.toml requirements.txt Gemfile go.mod 2>/dev/null  # stack and majors
ls CLAUDE.md AGENTS.md .cursorrules 2>/dev/null                              # binding; outranks these files
cat .env.example 2>/dev/null                                                  # config surface
ls migrations/ db/migrate/ alembic/versions/ 2>/dev/null | tail -5           # migration convention
```

Answer four questions: which framework and major version, where business logic already
lives, whether a typed error family exists, and which existing endpoint is the cleanest
example to copy. The reference endpoint matters most, because it carries conventions no
document describes.

## 3 · Greenfield or in flight

- **Empty repo or only scaffolding:** greenfield. You choose the stack (`foundation.md`).
- **Endpoints, services or migrations already shipped:** in flight. Match local naming,
  layout, response shape and error handling, even where these files would choose
  differently. List improvements separately, with costs. Don't reformat files you open.
- **Structure but no real code:** ask before treating it as greenfield.

## 4 · Feature build order

1. Name the reference endpoint you're copying (`architecture.md`)
2. Schema and migration, if new data is involved (`data-layer.md`)
3. Service function: pure business logic, no request or response objects (`architecture.md`)
4. Validation schema at the boundary (`security.md`)
5. Controller: parse, call service, shape response (`architecture.md`)
6. Typed errors, mapped by the central handler (`error-handling-logging.md`)
7. Service unit tests, then endpoint happy and unhappy paths (`testing.md`)

Step 3 is what keeps step 7 cheap: services get tested without an HTTP server.

## 5 · Invariants

These hold everywhere. A change that breaks one is wrong even if it runs and the tests pass.

1. **Layers point one way.** Routes, then services, then data access. Services never import request or response objects. (`architecture.md`)
2. **All external input is validated at the boundary.** Never trust a client-supplied type, presence or ID for authorization. (`security.md`)
3. **One response shape, one error handler.** Errors are typed and mapped centrally. No stack trace or DB error reaches a client. (`architecture.md`, `error-handling-logging.md`)
4. **No secrets in code, logs or git.** Config is loaded and validated once, at startup. (`foundation.md`, `security.md`)
5. **Schema changes are migrations.** Each has a working `up` and `down`. Never edit an applied migration. (`data-layer.md`)
6. **No N+1s and no unbounded loads.** Join known access patterns, paginate lists, cap page size server-side. (`data-layer.md`, `architecture.md`)
7. **Side effects are traceable.** Log who, what and when, without PII or secrets. (`error-handling-logging.md`)
8. **Identity and tenant come only from a verified credential.** Third-party tokens are verified, never decoded. (`security.md` §2)
9. **Money moves exactly once, atomically, for the amount the provider reports.** (`payments-billing.md`, `data-layer.md`)

## 6 · Working rules

Name the companion you followed, and the reference endpoint if the codebase has one. When
the codebase and a companion disagree, the codebase wins, and you say so. Ask only what the
code can't answer, mainly the auth model and tenancy shape, which have no safe default and
are costly to retrofit.

Finish with the project's lint, format and test commands. For schema changes, confirm `up`
and `down` work. List anything you deliberately left undone.
