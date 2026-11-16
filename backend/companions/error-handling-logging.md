---
name: error-handling-logging
description: Backend error handling and observability — one central handler, typed exceptions, structured and redacted logging, log levels, and health and metrics endpoints. Read when adding error handling, wiring up logging, or debugging a swallowed exception.
---

# Error handling & logging

> Fail loud in development and quiet toward the client in production. A raw exception or
> stack trace never reaches an API consumer.

Response shape → `architecture.md`. What counts as a secret in logs → `security.md` §4.

## 1 · Errors

- One global handler maps exceptions to the standard response shape. Don't copy try/catch into every route. In Express, use a single 4-argument error middleware, and wrap async handlers so rejections reach it. Otherwise they crash silently.
- **Operational errors** (bad input, not found, conflict) are expected. Return a clean 4xx using a typed exception: `NotFoundError`, `ValidationError`, `PermissionDeniedError`.
- **Programming errors** are bugs. Log them with full context, return a generic 500, and alert.
- Never swallow an error. No empty `catch {}` and no `except: pass`. Handle it, or log it with context and then rethrow or return explicitly.
- Never expose stack traces, library messages or internal details to clients. Log them internally and return a safe message.
- Use guard clauses over nested conditionals. Null-check external data (API, DB, SDK) before use, because it's `null` or `None` on failure paths.
- Errors carry the relevant IDs and the underlying cause. `throw new Error('Failed')` tells an on-call engineer nothing.

```js
if (!order) throw new ValidationError('No order');
if (order.amount <= 0) throw new ValidationError('Invalid amount');
try { return await chargeCard(order); }
catch (err) {
  logger.error('Payment failed', { orderId: order.id, err });
  throw new PaymentError('Unable to process payment', { orderId: order.id, cause: err });
}
```

## 2 · Logging

- Use structured JSON wherever logs are aggregated. No string concatenation.
- Every request's log lines carry a correlation ID, propagated to downstream calls.
- Log the operation, relevant IDs, duration and outcome. Never log PII, passwords, tokens, card numbers, or the other secret-like values listed in `security.md` §4.
- Levels: `debug` for diagnostics, `info` for normal events, `warn` for recoverable problems (retries, fallbacks), `error` for something that needs attention, `fatal` when the system is down. Don't log routine events at `error`. They drown the real alerts.
- No `console.log`, `print` or `debugger` in committed code.

```js
// Bad                                            // Good
console.log('Error');                             logger.error('Payment processing failed', { orderId: order.id, errorCode: err.code });
logger.info(`User ${user.email} logged in`);      logger.info('User login successful', { userId: user.id });
```

## 3 · Health and metrics

- `/health` (or `/healthz`) checks that critical dependencies (DB, cache) are reachable.
- Keep a separate liveness check that doesn't depend on them.
- Expose request count, latency and error rate for scraping on every production service.
- Alerts track real dependency health, not just "the process is up."

## 4 · Done when

- One central handler maps every exception to the standard shape
- No `catch` is empty, and no stack trace or DB error reaches a client
- Logs are structured, leveled correctly and free of PII and secrets; a correlation ID is present
- `/health` reflects real dependency status
