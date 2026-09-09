---
name: error-handling-logging
description: Backend error handling and observability — centralized error handling, typed exceptions, structured logging, log levels, and health/metrics endpoints. Read when adding error handling, wiring up logging, or debugging a swallowed exception.
---

# Error handling & logging

> Fail fast and loud in development; fail safe and quiet to the client in production. Never
> let a raw exception or stack trace reach an API consumer.

Response shape for error payloads → `architecture.md`. Input validation itself →
`security.md`.

## 1 · Error handling

- Centralize error handling with one global exception handler/middleware that maps
  exceptions to the standard error response shape — don't repeat the same try/catch
  boilerplate in every handler. In Express, a single 4-arg error-handling middleware; always
  call `next(err)` on error in async handlers (or use an async wrapper), or unhandled promise
  rejections crash silently.
- Distinguish **operational errors** (bad input, not found, conflict — expected, return a
  clean 4xx) from **programming errors/bugs** (unexpected — log with full context, return a
  generic 500, alert).
- Use custom/typed exception classes for expected domain errors (`NotFoundError`,
  `ValidationError`, `PermissionDeniedError`) instead of raising generic exceptions or
  returning magic error strings.
- Never swallow exceptions silently (`except: pass`, empty `catch {}`). At minimum, log them
  with context.
- Never expose internal error details, stack traces, or library error messages to clients in
  production. Log the detail internally; return a generic safe message externally.
- Guard clauses over nested conditionals — fail fast and make error paths explicit.

```js
// Bad — nested conditions, generic error
function processPayment(order) {
  if (order) {
    if (order.amount > 0) {
      if (order.customer) { return chargeCard(order); }
      else { throw new Error('No customer'); }
    } else { throw new Error('Invalid amount'); }
  } else { throw new Error('No order'); }
}

// Good — guard clauses, typed error, context
function processPayment(order) {
  if (!order) throw new ValidationError('No order');
  if (order.amount <= 0) throw new ValidationError('Invalid amount');
  if (!order.customer) throw new ValidationError('No customer');
  try {
    return chargeCard(order);
  } catch (err) {
    logger.error(`Payment failed for order ${order.id}`, { err });
    throw new PaymentError('Unable to process payment', { orderId: order.id, cause: err });
  }
}
```

**Null safety**: external data (API/DB/SDK results) can be `null`/`None` on failure paths —
always check before use.

```js
// Bad: crashes when device is null           // Good
const isOnline = device.online === true;      if (!device) { logger.warn(`No data for ${id}`); return; }
                                               const isOnline = device.online === true;
```

## 2 · Logging & observability

- Log in structured format (JSON) in any environment where logs are aggregated — not raw
  string concatenation.
- Include a correlation/request ID on every log line for a request, and propagate it through
  downstream service calls.
- Log operation, relevant IDs, duration, and outcome — never raw PII, passwords, tokens, or
  full credit card numbers. Redact before logging.
- No leftover `console.log`/`print` debugging in committed code — one log line per meaningful
  event.

```js
// Bad
console.log('Error');
logger.info(`User ${user.email} logged in`);

// Good
logger.error('Payment processing failed', {
  orderId: order.id, errorCode: err.code, duration: Date.now() - startTime,
});
logger.info('User login successful', { userId: user.id, duration: Date.now() - startTime });
```

- Use log levels correctly:

| Level | Use for |
|---|---|
| `debug` | detailed diagnostic info (variable values, function entry/exit) |
| `info` | significant, normal events (user login, order created) |
| `warn` | unexpected but recoverable (retry, fallback used) |
| `error` | needs attention (failed payment, DB connection lost) |
| `critical`/`fatal` | system is down |

Don't log routine operations at `error`.

- Expose a health-check endpoint (`/health` or `/healthz`) that checks critical dependencies
  (DB, cache) are reachable, and a separate liveness check that doesn't. Expose metrics
  (request count, latency, error rate) for scraping on any service running in production.

## 3 · Failure modes / anti-patterns to flag

| Anti-pattern | Issue | Fix |
|---|---|---|
| `try { ... } catch (e) {}` | silent failure, no trace | log with context and re-throw or handle explicitly |
| `throw new Error('Failed')` | no context to debug from | include relevant IDs and state |
| Stack trace returned in API response | leaks internals to clients | generic message externally, full detail in logs |
| `console.log` left in committed code | noisy, unstructured, no levels | remove or replace with the logger |
| PII/secret in a log line | compliance and leak risk | redact before logging |
| Routine event logged at `error` | drowns real alerts | use `info`/`debug` |

## 4 · Done when

- One centralized handler maps exceptions to the standard error response shape
- Every `catch`/`except` either handles the error meaningfully or logs it with context —
  none are empty
- No stack trace or raw DB/library error reaches a client response
- Logs are structured, leveled correctly, and free of PII/secrets
- A request/correlation ID is present and propagated across a request's logs
- `/health` (or equivalent) reflects real dependency status
