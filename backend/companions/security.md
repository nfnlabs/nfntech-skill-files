---
name: security
description: Backend security — input validation, authentication vs authorization, verifying third-party identity tokens, tenant scoping, secrets handling, injection prevention, webhooks, outbound requests to user-supplied URLs, security headers, CORS, and rate limiting. Read when adding an endpoint that accepts input, handles auth, or touches secrets, or when reviewing a diff for security issues.
---

# Security

> Never trust client input, never trust a client-supplied ID for authorization, and never let
> a secret reach code, logs, or git history.

Rate limiting at the infra layer (Nginx, Redis-backed limiters) → `performance-deployment.md`.
Response-shape and status-code conventions for rejected input → `architecture.md`.
Payments, credits and billing webhooks → `payments-billing.md`. Model calls, AI-generated
content and AI cost abuse → `ai-features.md`.

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

**Verify every identity token you did not issue.** A Google ID token, an Apple identity token,
a Shopify session token or any other provider JWT is only proof of identity after its
signature, `aud` (your client ID), `iss` and `exp` have been checked — use the provider's
library (`google-auth-library`'s `verifyIdToken`, `@shopify/shopify-api`'s session-token
decoder) rather than hand-rolling. `jwt.decode()` reads a token without checking it; it must
never sit on an authentication path. "The client already verified it" is not verification.

```js
// Bad — anyone can forge this token and sign in as anyone
const { sub, email } = jwt.decode(req.body.idToken);

// Good — signature, audience, issuer and expiry are all checked
const ticket = await googleClient.verifyIdToken({ idToken: req.body.idToken, audience: config.googleClientId });
const { sub, email } = ticket.getPayload();
```

For tokens you issue yourself: pin the algorithm, require `exp`, set an `aud` per token kind,
and when one secret signs several kinds (merchant, shopper, staff, service), make each route
check the kind it expects — a shopper token must not pass a merchant check because the
signature is valid.

**Take the tenant from the credential, never from the request.** In a multi-tenant system
(shops, organizations, workspaces) the tenant a request acts on comes from the verified
token or session — never from a header, query parameter or body field, even one that
"should match". Resolve it once in the auth middleware (`req.tenant`) and have every query
scope by it; a handler that re-reads `req.query.shop` after authentication has reopened the
hole the middleware closed. The same holds for the acting user inside a tenant: never fall
back to a client-supplied user or customer ID when the token doesn't carry one.

```js
// Bad — middleware verified the header's shop; the handler trusts the query's
router.get('/customers', authenticateShop, async (req, res) => {
  const shop = await Shop.findOne({ where: { domain: req.query.shop } });
  ...
});

// Good — one source of truth for the tenant
router.get('/customers', authenticateShop, async (req, res) => {
  const customers = await customerService.list({ shopId: req.tenant.id, ...paging(req) });
  ...
});
```

Sequential integer IDs make every missing ownership check exploitable by counting; scope
every lookup by tenant **and** owner (`where: { id, shopId, customerId }`), and prefer
non-guessable public IDs for resources fetched by ID.

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

A secret that reached git is leaked even after the commit is reverted: rotate it the same
day. That includes "master" tokens, test backdoors and shared admin passwords — which should
not exist in the first place.

**No authentication bypass outside a developer's machine.** A shortcut that skips auth in
development (`if (NODE_ENV === 'development') trustHeader()`, `SKIP_AUTH=true`) is one
mis-set environment variable away from production. If one is needed, gate it on something a
deployed server cannot have (bound to `127.0.0.1` only), and make the server refuse to start
when the flag is set in any deployed environment.

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

- Check limits and quotas **before** storing a file or calling a paid validator, and upload
  to a temporary prefix (with an object-storage lifecycle rule that expires it) until the
  file passes validation.
- Deleting a record deletes its files — including derived ones (thumbnails, generated
  results). A soft-deleted row whose image stays in the bucket forever is a privacy defect.
- Treat a pre-signed URL as a bearer credential for its lifetime: never log it, keep expiry
  short, and log the object key instead.

## 7 · Rate limiting & abuse

Rate-limit authentication endpoints and any expensive/public endpoint. Add brute-force
lockout or backoff on login/OTP/password-reset flows. Key limits on the **authenticated identity**
(user, tenant, API key) after authentication, plus IP for anonymous routes — never on a
header or parameter the client can omit or rotate. With more than one process or instance,
keep counters in a shared store (Redis, the database); an in-memory map gives each process
its own limit. Any endpoint that costs money per call (AI models, SMS, paid APIs) needs a
per-user limit and a spend cap. (Infra-level and distributed rate
limiting configuration lives in `performance-deployment.md`.)

## 8 · Dependencies

Keep dependencies patched; run a vulnerability scanner (`pip-audit`/`npm audit`/
`bundler-audit`/Dependabot/Snyk) in CI, not manually and occasionally. Prefer well-maintained,
widely-used libraries for security-sensitive functionality (auth, crypto, serialization) over
hand-rolled or unmaintained ones.

## 9 · Webhooks and server-to-server calls

- Verify the provider's signature over the **raw request bytes** — mount a raw-body parser on
  the webhook route before any JSON parser. `HMAC(JSON.stringify(req.body))` is not the
  signed payload and fails (or passes) unpredictably.
- Compare signatures in constant time (`crypto.timingSafeEqual` after a length check), never
  with `===`/`!==`.
- Process each event once: store the provider's event or delivery ID under a unique
  constraint and skip duplicates. Providers retry; handlers must be idempotent.
- Don't trust the payload for anything that grants value — re-fetch the object (payment,
  subscription, order) from the provider's API by ID and act on that record
  (→ `payments-billing.md`).
- An endpoint that only your own services call (one app forwarding a webhook to another)
  authenticates with a server-to-server secret or mTLS that never reaches a browser. A user's
  or merchant's session token proves who they are, not that a request came from your server.
- Admin and maintenance endpoints (reset, re-sync, grant) sit behind internal admin auth,
  never behind the same auth customers have.

## 10 · Outbound requests to user-supplied URLs (SSRF)

Whenever the server fetches a URL that came from a client (image URLs, webhooks a user
registers, link previews, imports), an attacker can point it at your internal network or the
cloud metadata endpoint (`169.254.169.254`).

- Prefer an allow-list of hosts (your CDN, the platform's CDN) over a block-list.
- Otherwise: accept `https` only; resolve the hostname and reject private, loopback,
  link-local and unique-local ranges (IPv4 and IPv6); connect to the IP you checked so DNS
  can't change in between; disable redirects or re-check each hop.
- Cap response size (`maxContentLength`) and time, and check the content type.
- Never return the fetch error's text to the client — "connect ECONNREFUSED 10.0.0.5:80"
  turns the endpoint into a port scanner.

Use a maintained library for the IP checks (`ssrf-req-filter`, `request-filtering-agent`
for Node) rather than a hand-written regex.

## 11 · Failure modes / anti-patterns to flag

| Anti-pattern | Issue | Fix |
|---|---|---|
| `User.find({...req.query})` | client controls the query shape | validate and allowlist fields |
| Authorization check by role only | misses per-resource ownership (IDOR) | check ownership explicitly |
| Secret in a log line or error message | leaks on any log aggregation | redact before logging |
| `Access-Control-Allow-Origin: *` with credentials | any site can read authenticated responses | explicit origin allowlist |
| Client-supplied filename used as-is | path traversal / overwrite risk | generate the storage name server-side |
| Raw input concatenated into a query/shell command | injection | parameterized queries, `execFile` over `exec` |
| `jwt.decode(token)` on a login path | anyone can forge the token | provider library verify with `aud`/`iss`/`exp` |
| Tenant read from `req.query`/headers after auth | cross-tenant access with a valid token | use the tenant resolved from the credential |
| Customer/user ID falls back to a header when the token lacks one | impersonation | reject the request |
| Webhook HMAC over re-serialised JSON, compared with `!==` | valid events rejected, timing leak | raw body, `timingSafeEqual` |
| Webhook handler with no event-ID dedupe | retries apply twice | unique constraint on event ID |
| `axios.get(req.body.imageUrl)` | SSRF into internal network | allow-list or IP-checked fetch with size cap |
| `if (NODE_ENV === 'development') skipAuth()` | open server when env is mis-set | localhost-only, refuse to start when deployed |
| Signed URL or token prefix in a log line | log readers can open private files | log the object key / token ID only |
| Rate limit keyed on a client-chosen header, in memory | bypass by omitting it; per-process limits | key on authenticated identity, shared store |

## 12 · Done when

- Every external input is validated at the boundary before use
- Every protected route checks both authentication and resource-level authorization
- No secret is hardcoded, logged, or committed (`git diff | grep -iE "key|token|secret|password"` clean)
- Passwords hashed with bcrypt/argon2/scrypt; queries parameterized
- Security headers and an explicit CORS allowlist are in place
- Third-party identity tokens are verified (signature, `aud`, `iss`, `exp`), never decoded
- The tenant and acting user come only from the verified credential; every query scopes by them
- Webhooks verify the signature on the raw body in constant time and dedupe by event ID
- Server-fetched URLs are allow-listed or IP-checked, size- and time-capped
- No auth bypass can be enabled on a deployed server
- Auth/expensive endpoints are rate-limited by authenticated identity in a shared store
