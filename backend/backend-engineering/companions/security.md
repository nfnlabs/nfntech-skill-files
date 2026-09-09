---
name: security
description: Backend security — input validation, authentication vs authorization, secrets handling, injection prevention, security headers, CORS, and rate limiting. Read when adding an endpoint that accepts input, handles auth, or touches secrets, or when reviewing a diff for security issues.
---

# Security

> Never trust client input, never trust a client-supplied ID for authorization, and never let
> a secret reach code, logs, or git history.

Rate limiting at the infra layer (Nginx, Redis-backed limiters) → `performance-deployment.md`.
Response-shape and status-code conventions for rejected input → `architecture.md`.

## 1 · Input validation

Validate and coerce **all** external input — body, query params, path params, headers,
cookies — at the boundary using a schema/type system (Pydantic, Zod, JSON Schema, Rails
strong params). Never trust client-supplied types or presence, even if the client also
validates. Reject invalid input immediately with a clear message.

```js
// Bad — no validation
app.post('/users/:id', (req, res) => {
  const user = User.findByIdAndUpdate(req.params.id, req.body);
  res.json(user);
});

// Good — validate input
app.post('/users/:id', (req, res) => {
  const schema = z.object({
    name: z.string().min(1).max(100),
    email: z.string().email(),
    age: z.number().int().min(0).max(150),
  });
  const validated = schema.parse(req.body);
  const user = User.findByIdAndUpdate(req.params.id, validated);
  res.json(user);
});
```

## 2 · Authentication vs authorization

Verify identity first, then explicitly check permission for the specific resource/action
being accessed — including object-level ownership checks, not just role checks. This is what
prevents IDOR bugs. Never trust a client-supplied ID for authorization.

```js
// Bad — user can edit anyone's profile
app.put('/users/:id', (req, res) => {
  const user = User.findByIdAndUpdate(req.params.id, req.body);
  res.json(user);
});

// Good — verify ownership
app.put('/users/:id', authenticate, (req, res) => {
  if (req.user.id !== parseInt(req.params.id)) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  const user = User.findByIdAndUpdate(req.params.id, req.body);
  res.json(user);
});
```

## 3 · Injection prevention

Always use parameterized queries / ORM query builders. Never string-concatenate or
template user input into SQL, shell commands, or NoSQL queries — not even for "trusted"
internal values. Escape/encode all output rendered into HTML and rely on the templating
engine's autoescaping rather than disabling it; sanitize (don't just block) rich-text/HTML
user input that must be rendered.

## 4 · Secrets

Never hardcode secrets (API keys, DB credentials, signing keys) — load via environment
variables or a secrets manager through a config wrapper. Never commit them, never log them.
Add a `.env.example` with dummy values; keep `.env` in `.gitignore`.

```js
// Bad
const apiKey = 'sk_live_abc123';
logger.info(`Using API key: ${apiKey}`);

// Good
const apiKey = config.stripeApiKey; // from env, via one config module
logger.info('Initializing Stripe');
```

Hash passwords with a slow, salted algorithm (bcrypt/argon2/scrypt). Never store plaintext or
reversibly-encrypted passwords. Never roll your own crypto.

## 5 · Headers, CORS, CSRF

- Set security headers by default: `Content-Security-Policy`, `X-Content-Type-Options:
  nosniff`, `Strict-Transport-Security`, `X-Frame-Options`/`frame-ancestors`. Use a framework
  middleware/gem/package (`helmet`, `flask-talisman`) rather than hand-rolling.
- Configure CORS explicitly with an allowlist of origins — never
  `Access-Control-Allow-Origin: *` on an endpoint that accepts credentials.
- Use CSRF protection for any cookie-authenticated, state-changing endpoint reachable from a
  browser. Not needed for pure token-bearer APIs without cookies.
- Enforce HTTPS/TLS in production; redirect HTTP → HTTPS at the edge.

## 6 · Files and uploads

Validate uploaded file type and size server-side; store outside the web root; never trust a
client-supplied filename or `Content-Type`. Set explicit request size limits and timeouts
(body size, upload size, connection timeout) to bound resource usage per request.

## 7 · Rate limiting & abuse

Rate-limit authentication endpoints and any expensive/public endpoint. Add brute-force
lockout or backoff on login/OTP/password-reset flows. (Infra-level and distributed rate
limiting configuration lives in `performance-deployment.md`.)

## 8 · Dependencies

Keep dependencies patched; run a vulnerability scanner (`pip-audit`/`npm audit`/
`bundler-audit`/Dependabot/Snyk) in CI, not manually and occasionally. Prefer well-maintained,
widely-used libraries for security-sensitive functionality (auth, crypto, serialization) over
hand-rolled or unmaintained ones.

## 9 · Failure modes / anti-patterns to flag

| Anti-pattern | Issue | Fix |
|---|---|---|
| `User.find({...req.query})` | client controls the query shape | validate and allowlist fields |
| Authorization check by role only | misses per-resource ownership (IDOR) | check ownership explicitly |
| Secret in a log line or error message | leaks on any log aggregation | redact before logging |
| `Access-Control-Allow-Origin: *` with credentials | any site can read authenticated responses | explicit origin allowlist |
| Client-supplied filename used as-is | path traversal / overwrite risk | generate the storage name server-side |
| Raw input concatenated into a query/shell command | injection | parameterized queries, `execFile` over `exec` |

## 10 · Done when

- Every external input is validated at the boundary before use
- Every protected route checks both authentication and resource-level authorization
- No secret is hardcoded, logged, or committed (`git diff | grep -iE "key|token|secret|password"` clean)
- Passwords hashed with bcrypt/argon2/scrypt; queries parameterized
- Security headers and an explicit CORS allowlist are in place
- Auth/expensive endpoints are rate-limited
