---
name: performance-deployment
description: Backend performance and production readiness — caching, rate limiting, connection pooling, PM2/process management, Nginx configuration, and the pre-deploy checklist. Read when tuning for load, configuring infra, or preparing a service to ship.
---

# Performance & deployment

> Measure before optimizing — profile or use APM data to find the actual bottleneck instead
> of guessing.

Query-level performance (indexes, N+1) → `data-layer.md`. Application-level rate limiting on
a single route vs. infra-level distributed limiting are both covered here.

## 1 · Rate limiting

Rate limiting protects endpoints from abuse and ensures fair resource usage. Rate-limit
authentication endpoints strictly; API endpoints moderately; public/anonymous endpoints
loosely.

```js
const rateLimit = require('express-rate-limit');

const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, max: 5,
  message: 'Too many login attempts, please try again later',
});

const apiLimiter = rateLimit({
  windowMs: 60 * 1000, max: 100,
  keyGenerator: (req) => req.user?.id || req.ip,
});

app.post('/auth/login', authLimiter, loginController);
app.get('/api/users', apiLimiter, getUsersController);
```

For multiple server instances, back the limiter with Redis so limits are shared across
processes:

```js
const RedisStore = require('rate-limit-redis');
const limiter = rateLimit({
  store: new RedisStore({ client: redisClient, prefix: 'rate-limit:' }),
  windowMs: 15 * 60 * 1000, max: 100,
});
```

Nginx can enforce the same idea at the edge, ahead of the app:

```nginx
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

location /auth/login { limit_req zone=auth burst=2 nodelay; proxy_pass http://api_backend; }
location /api/       { limit_req zone=api  burst=10 nodelay; proxy_pass http://api_backend; }
```

## 2 · Caching

Cache expensive, frequently-read, rarely-changing data (Redis/in-memory) with an explicit
invalidation strategy — never cache without a plan to invalidate it.

```js
app.get('/api/posts', async (req, res) => {
  const cached = await client.get('posts:all');
  if (cached) return res.json({ data: JSON.parse(cached), source: 'cache' });

  const posts = await Post.find().limit(100);
  await client.setex('posts:all', 600, JSON.stringify(posts)); // 10 min TTL
  res.json({ data: posts, source: 'db' });
});

app.put('/api/posts/:id', async (req, res) => {
  const post = await Post.findByIdAndUpdate(req.params.id, req.body);
  await client.del('posts:all'); // invalidate on update
  res.json(post);
});
```

Stream large responses/file downloads instead of loading the entire payload into memory.

## 3 · Connections and timeouts

Use connection pooling; never open a new raw connection per request. Set sane timeouts on
every outbound call (DB, HTTP, cache) — an unbounded call can exhaust the pool for the whole
service.

```js
const pool = new Pool({ /* ... */ max: 20, idleTimeoutMillis: 30000, connectionTimeoutMillis: 2000 });

const client = axios.create({ timeout: 5000 });
```

## 4 · Graceful shutdown

Finish in-flight requests and close DB/queue connections cleanly on `SIGTERM` before exiting.

```js
process.on('SIGTERM', async () => {
  server.close(async () => {
    await db.close();
    await redis.quit();
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 30000); // forced exit if graceful shutdown hangs
});
```

## 5 · Process management (PM2) and reverse proxy (Nginx)

```js
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'api-server', script: './server.js',
    instances: 'max', exec_mode: 'cluster',
    max_memory_restart: '500M', max_restarts: 10, min_uptime: '10s',
  }],
};
```

```nginx
upstream api_backend {
  least_conn;
  server 127.0.0.1:3000;
  server 127.0.0.1:3001;
  keepalive 32;
}

server {
  listen 443 ssl http2;
  gzip on; gzip_types text/plain text/css application/json application/javascript;
  client_max_body_size 10M;
  proxy_connect_timeout 60s; proxy_send_timeout 60s; proxy_read_timeout 60s;

  location / { proxy_pass http://api_backend; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; }
  location ~* \.(js|css|png|jpg|svg|woff2)$ { expires 1y; add_header Cache-Control "public, immutable"; }
  location /health { access_log off; proxy_pass http://api_backend; }
}
```

## 6 · Deployment readiness

- The app starts from a clean environment using only checked-in config templates +
  documented env vars — no manual, undocumented setup steps.
- Never run the framework's debug mode, auto-reload, or verbose error pages in production.
- Container images run as a non-root user and include only what's needed to run the app.
- Pin dependency versions (lockfile) so builds are reproducible.

## 7 · Pre-deploy checklist

- [ ] Rate limiting configured on public and auth endpoints
- [ ] Timeouts set on all outbound calls and, where relevant, per-route
- [ ] Connection pooling configured for the database
- [ ] Caching strategy implemented with an invalidation path
- [ ] Gzip compression and static-asset cache headers enabled
- [ ] PM2 (or equivalent) configured with restart policies and memory limits
- [ ] Nginx (or equivalent) reverse proxy with SSL and load balancing
- [ ] Health-check endpoint implemented and load-balancer-aware
- [ ] Graceful shutdown handles `SIGTERM`
- [ ] Database indexes match actual query patterns; no known N+1s
- [ ] Monitoring/alerting wired to real dependency checks, not just process-up
- [ ] Debug mode / verbose error pages disabled

## 8 · Done when

- Every checklist item above is checked or explicitly deferred with a reason
- Load test or profiling data backs any performance claim — nothing optimized on a guess
- A `SIGTERM` during a live request completes that request before the process exits
