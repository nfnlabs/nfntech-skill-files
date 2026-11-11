---
name: backend-engineering
description: Owns server-side/API engineering across languages and frameworks (Node/Express, Python FastAPI/Django/Flask, Rails, and others) — the entry point that reads what a project already is, then routes to the companion file owning the area being touched. Triggers on any backend work — new endpoints, services, database/schema changes, auth, payments and credits, webhooks, AI model integrations, error handling, logging, caching, performance tuning, deployment config, tests, and code review.
---

# Backend engineering

> Read the codebase before advising it, then open exactly one companion. An existing
> convention outranks anything written in these files.

## 1 · Route by task

| The task | Open |
|---|---|
| New service bootstrap, project layout, config/env loading, concurrency basics | `companions/foundation.md` |
| Routes/controllers, layering, REST conventions, response shape, versioning, framework idioms | `companions/architecture.md` |
| Schema, migrations, queries, indexing, transactions, connection pooling, naming | `companions/data-layer.md` |
| AuthN/authZ, input validation, secrets, headers, CORS, injection risks | `companions/security.md` |
| Exceptions, centralized error handling, structured logging, observability | `companions/error-handling-logging.md` |
| Caching, rate limiting, PM2/process management, Nginx, deployment readiness | `companions/performance-deployment.md` |
| Unit/integration tests, mocking, coverage targets, CI gates | `companions/testing.md` |
| Payments, credits/usage balances, subscriptions, refunds, billing webhooks | `companions/payments-billing.md` |
| Anything that calls an AI model (LLM, image generation, vision, moderation) or stores its output | `companions/ai-features.md` |
| Reviewing a PR/diff, anti-patterns, approve vs request-changes | `companions/code-review.md` |

One companion, occasionally two. Loading all ten for one change buries the answer under
context that doesn't apply.

## 2 · Read the project first

Never skip this on a codebase that already exists — every companion's advice is a comparison
against what's there, and you can't compare against an assumption.

```sh
cat package.json pyproject.toml requirements.txt Gemfile go.mod 2>/dev/null   # stack and majors
ls CLAUDE.md AGENTS.md .cursorrules 2>/dev/null       # binding; outranks these files
find . -maxdepth 3 -type d \( -name node_modules -o -name .git -o -name venv \) -prune -o -type d -print | sort
grep -rl "express()\|FastAPI(\|Flask(\|Rails.application" . --include="*.{js,ts,py,rb}" 2>/dev/null | head
cat .env.example 2>/dev/null                          # required config surface
ls migrations/ db/migrate/ alembic/versions/ 2>/dev/null | tail -5   # migration convention
```

Four answers decide how your change should look: **which framework and major version**
(validation and DI idioms changed shape across Express 4→5, FastAPI's dependency system,
Django REST Framework versions), **where business logic already lives** (services, use
cases, `app/services/`), **whether a typed error family exists**, and **which existing
endpoint is the cleanest example** to copy. That last one is the most valuable — a named
reference implementation carries a hundred conventions no document can describe.

## 3 · Greenfield or in flight

| Signal | Then |
|---|---|
| Empty repo, or only framework scaffolding (`create-express-app`, `django-admin startproject`) | **Greenfield** — you choose the stack; `companions/foundation.md` has the defaults and the build order |
| Endpoints, services or migrations already shipped | **In flight** — the codebase has answered most questions; extend it consistently |
| Structure but no code worth keeping | ask before treating it as greenfield |

In flight means: adopt, then propose. Match local naming, folder layout, response shape and
error handling, including idioms these files would not have chosen. Improvements are a
separate short list with costs attached, not applied inside an unrelated change. Don't
reformat files you happened to open, and don't "fix" an undocumented deliberate choice
without asking.

## 4 · Feature build order

The one sequence worth stating here, because working outward from the route produces
services shaped by HTTP convenience:

1. Name the reference endpoint you're copying — `architecture.md`
2. Schema/migration first if new data is involved — `data-layer.md`
3. Service function: pure business logic, no request/response objects — `architecture.md`
4. Input validation schema at the boundary — `security.md`
5. Controller/route: parse input → call service → shape response — `architecture.md`
6. Typed errors mapped by the centralized handler — `error-handling-logging.md`
7. Tests: service unit tests, then endpoint happy/unhappy paths — `testing.md`

Step 3's separation isn't a style preference; it's what makes step 7 cheap without spinning
up an HTTP server for every test.

## 5 · Invariants

These hold in every companion, so they're stated once. A change breaking one is wrong even
when it runs and the tests pass.

1. **Layers point one way** — routing/controllers → services (business logic) → data access.
   Services never import framework request/response objects.
2. **All external input is validated at the boundary** — body, query, params, headers — before
   business logic runs. Never trust a client-supplied type, presence, or ID for authorization.
3. **One response shape for the whole API.** Success and error payloads never disagree in
   structure between two endpoints.
4. **Typed errors, centralized handling.** Domain errors are typed exceptions; one handler
   maps them to the response shape. No raw stack trace or DB error reaches a client.
5. **No secrets in code, logs, or git.** Config comes from env vars/a secrets manager, loaded
   and validated once at startup — never hardcoded, never read ad hoc mid-request.
6. **Schema changes are migrations, always.** Never hand-edit a production schema or an
   already-applied migration; never use ORM auto-sync against a real environment.
7. **No N+1s, no unbounded loads.** Batch/join known access patterns; paginate any list that
   can grow unbounded; cap page size server-side.
8. **Every side-effecting operation is traceable** — logged with context (who/what/when) at
   the point it happens, without leaking PII or secrets.
9. **Identity and tenant come only from a verified credential.** Tokens from other providers
   are verified (signature, audience, issuer, expiry), never just decoded; the tenant and
   acting user are read from the credential, never from a header, query or body.
10. **Money moves exactly once, atomically.** Amounts and plans come from your catalog or the
    payment provider, never the client; every payment is applied once under a unique key;
    balances change only through conditional or relative updates with a ledger row in the
    same transaction.

## 6 · Working rules

Say which companion you followed and, on an existing codebase, which reference endpoint you
copied — it makes a wrong route cheap to correct. Where the codebase and a companion
disagree, the codebase wins and you say so. Ask only what the code can't answer: the auth
model and multi-tenancy shape have no safe default and are expensive to retrofit. Everything
else is visible in the repo or has a defensible default.

Finish with the project's lint/format/test commands and, for schema changes, confirm the
migration has a working `up` and `down`. Name anything you deliberately left undone.
