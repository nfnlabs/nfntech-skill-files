---
name: performance-deployment
description: Backend performance and production readiness — rate-limit mechanics, caching, connection pooling and timeouts, graceful shutdown, PM2, Nginx, and the pre-deploy checklist. Read when tuning for load, configuring infra, or preparing a service to ship.
---

# Performance & deployment

> Measure before optimizing. Use profiling or APM data to find the real bottleneck, not a guess.

Query-level performance (indexes, N+1) → `data-layer.md`. Rate-limit policy → `security.md` §7.

## 1 · Rate-limit mechanics

Limit auth endpoints strictly, the API moderately and public routes loosely. On a single
process, use middleware:

```js
const authLimiter = rateLimit({ windowMs: 15 * 60 * 1000, max: 5 });
const apiLimiter  = rateLimit({ windowMs: 60 * 1000, max: 100, keyGenerator: (req) => req.user?.id || req.ip });
app.post('/auth/login', authLimiter, loginController);
```

With multiple instances, back the counters with a shared store so limits aren't per process:
`store: new RedisStore({ client: redisClient, prefix: 'rate-limit:' })` (`rate-limit-redis`).

Nginx can enforce the same limits at the edge:

```nginx
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
location /auth/login { limit_req zone=auth burst=2 nodelay; proxy_pass http://api_backend; }
```

## 2 · Caching

Cache expensive, frequently read, rarely changing data (Redis or in-memory). Every cache
entry needs a TTL and an invalidation path on write. Never cache without an invalidation
plan. Stream large responses and file downloads instead of buffering them in memory.

## 3 · Connections and timeouts

- Use a connection pool. Never open a raw connection per request.
- Set a timeout on every outbound call (DB, HTTP, cache). An unbounded call can exhaust the pool for the whole service.

```js
new Pool({ max: 20, idleTimeoutMillis: 30000, connectionTimeoutMillis: 2000 });
axios.create({ timeout: 5000 });
```

## 4 · Graceful shutdown

On `SIGTERM`: stop accepting connections, finish in-flight requests, close DB and queue
connections, then exit. Force an exit after a deadline (about 30 seconds) if shutdown hangs.

## 5 · Process management and Nginx

- **PM2** (or equivalent): cluster mode across cores, a restart policy (`max_restarts`, `min_uptime`), and a memory limit (`max_memory_restart`).
- **Nginx** (or equivalent): TLS terminated, with HTTP redirected to HTTPS; `gzip` for text and JSON; a body size limit (`client_max_body_size`); proxy timeouts; a `least_conn` upstream with keepalive; long-lived immutable cache headers for hashed static assets; access logging off for the health route.

## 6 · Pre-deploy checklist

- [ ] Rate limits on public and auth endpoints (shared store if multi-instance)
- [ ] Timeouts on every outbound call; connection pool configured
- [ ] Caching has an invalidation path
- [ ] Gzip and static-asset cache headers on
- [ ] PM2 (or equivalent) with restart policy and memory limit
- [ ] Nginx (or equivalent) with SSL, load balancing, body-size limit and timeouts
- [ ] Health check implemented and load-balancer aware; graceful `SIGTERM` handling
- [ ] Indexes match real query patterns; no known N+1s
- [ ] Monitoring wired to real dependency checks (`error-handling-logging.md` §3)
- [ ] Debug mode, auto-reload and verbose error pages off in production
- [ ] App starts from a clean environment using only checked-in templates and documented env vars
- [ ] Container runs as non-root with only what it needs; dependencies pinned by lockfile

## 7 · Done when

- Every checklist item is checked, or deferred with a reason
- Any performance claim is backed by load-test or profiling data
- A `SIGTERM` during a live request completes that request before the process exits
