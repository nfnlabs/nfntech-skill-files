---
name: security
description: Backend security — input validation, authentication vs authorization, verifying third-party identity tokens, tenant scoping, secrets, injection, headers and CORS, uploads, rate-limit policy, webhooks, and outbound requests to user-supplied URLs (SSRF). Read when adding an endpoint that takes input, handles auth or secrets, or reviewing for security issues.
---

# Security

> Never trust client input or a client-supplied ID for authorization. Never let a secret
> reach code, logs or git history.

Response shape for rejected input → `architecture.md`. Payments and billing webhooks →
`payments-billing.md`. Model calls and AI cost → `ai-features.md`. Rate-limit mechanics →
`performance-deployment.md` §1.

## 1 · Input validation

Validate and coerce all external input (body, query, params, headers, cookies) at the
boundary, with a schema (Zod, Pydantic, JSON Schema, Rails strong params). Don't trust
client types or presence, even when the client also validates. Reject immediately, with a clear message.

```js
const body = z.object({ name: z.string().min(1).max(100), age: z.number().int().min(0).max(150) }).parse(req.body);
```

## 2 · Authentication and authorization

Verify identity first, then check permission for this specific resource and action,
including ownership. A role check alone allows IDOR.

```js
// Bad: any user can edit any profile          // Good: ownership check
app.put('/users/:id', auth, (req, res) => {    app.put('/users/:id', auth, (req, res) => {
  res.json(User.update(req.params.id, req.body));   if (req.user.id !== Number(req.params.id)) return res.status(403).end();
});                                               res.json(User.update(req.params.id, req.body));
                                                });
```

**Third-party identity tokens** (Google, Apple, Shopify session tokens, any provider JWT)
prove identity only after signature, `aud`, `iss` and `exp` have been checked, using the
provider's library. `jwt.decode()` reads a token without checking it, so it never belongs
on an auth path. "The client already verified it" is not verification.

```js
const ticket = await googleClient.verifyIdToken({ idToken, audience: config.googleClientId });
const { sub, email } = ticket.getPayload();
```

**Tokens you issue:** pin the algorithm, require `exp`, and set an `aud` per token kind. If
one secret signs several kinds (merchant, shopper, staff), each route checks the kind it
expects. A shopper token must not pass a merchant check.

**The tenant comes from the credential, never the request.** In a multi-tenant system, the
tenant and the acting user come from the verified token or session, never from a header,
query or body, even if the value "should match." Resolve the tenant once in auth middleware
(`req.tenant`) and scope every query by it. If the token carries no customer or user ID,
reject the request. Don't fall back to a client-supplied one.

```js
// Bad: the handler re-reads the tenant from the query      // Good
const shop = await Shop.findOne({ where: { domain: req.query.shop } });   const list = await customerService.list({ shopId: req.tenant.id, ...paging(req) });
```

Scope every lookup by tenant and owner (`where: { id, shopId, customerId }`). Sequential
integer IDs can be counted, so prefer non-guessable public IDs for resources fetched by ID.

## 3 · Injection

Use parameterized queries or the ORM's query builder. Never concatenate or template user
input into SQL, shell commands or NoSQL queries, even for "trusted" internal values. Use
`execFile` over `exec`. Rely on the template engine's autoescaping rather than disabling
it. Sanitize rich-text input, don't just block it.

## 4 · Secrets and logs

- Load secrets from env vars or a secrets manager, through the config module. Never hardcode, log or commit them. Keep `.env` in `.gitignore` and a `.env.example` with dummy values.
- A secret that reached git is leaked, even after a revert. Rotate it the same day. Master tokens, test backdoors and shared admin passwords shouldn't exist at all.
- Redact before logging: secrets, token prefixes, signed storage URLs, webhook signatures, full request headers and full provider payloads. Log IDs instead (object key, token ID, event ID, job ID). `error-handling-logging.md` covers the logging rules.
- Hash passwords with bcrypt, argon2 or scrypt. Never store plaintext or reversibly encrypted passwords. Never roll your own crypto.

```js
// Bad                                       // Good
logger.info(`Using key ${apiKey}`);          logger.info('Initializing Stripe'); // key comes from config.stripeApiKey
```

**No auth bypass on a deployed server.** A development shortcut (`NODE_ENV === 'development'`
trusting a header, or `SKIP_AUTH=true`) is one mis-set variable away from production. If one
is needed, bind it to `127.0.0.1` only, and refuse to start when it's set in any deployed environment.

## 5 · Headers, CORS and TLS

- Set security headers by default: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`, `frame-ancestors`. Use `helmet` or `flask-talisman`, not hand-rolled headers.
- CORS: an explicit origin allowlist. Never `Access-Control-Allow-Origin: *` with credentials.
- CSRF protection for cookie-authenticated, state-changing endpoints. Not needed for pure bearer-token APIs.
- HTTPS in production, with HTTP redirected at the edge.

## 6 · Uploads and stored files

- Validate type and size on the server. Store outside the web root. Generate the storage name server-side. Never trust a client filename or `Content-Type` as-is.
- Set explicit request size and time limits.
- Check quotas before storing a file or calling a paid validator. Upload to a temporary prefix with an expiry lifecycle rule until the file passes validation.
- Deleting a record deletes its files, including derived ones (thumbnails, generated results). A soft-deleted row whose image stays in the bucket is a privacy defect.
- A pre-signed URL is a bearer credential for its lifetime. Never log it, and keep its expiry short.

## 7 · Rate-limit policy and abuse

Rate-limit authentication endpoints, expensive endpoints and public endpoints. Add lockout or
backoff on login, OTP and password reset. Key limits on the authenticated identity (user,
tenant, API key), with IP only for anonymous routes. Never key on a header or parameter the
client can omit or rotate. With more than one instance, count in a shared store (Redis, the
database). An in-memory counter gives each process its own limit. Any call that costs money
per request needs a per-user limit and a spend cap. Mechanics are in `performance-deployment.md` §1.

## 8 · Webhooks and server-to-server calls

- Verify the signature over the **raw request bytes**. Mount a raw-body parser on the route before any JSON parser. Re-serialized JSON is not the signed payload.
- Compare signatures in constant time (`crypto.timingSafeEqual`, after a length check). Never `===` or `!==`.
- Store the provider's event or delivery ID under a unique constraint, and skip duplicates. Providers retry, so handlers must be idempotent.
- Don't trust the payload for anything that grants value. Re-fetch the object by ID from the provider's API and act on that record (`payments-billing.md`).
- A service that only your own services call authenticates with a server-to-server secret or mTLS. A user's session token proves who they are, not that the request came from your server.
- Admin and maintenance endpoints (reset, re-sync, grant) sit behind internal admin auth, never the auth customers use.

## 9 · Outbound requests to user-supplied URLs (SSRF)

When the server fetches a client-supplied URL (image URLs, user-registered webhooks, link
previews, imports), an attacker can point it at your internal network or at the cloud
metadata address `169.254.169.254`.

- Prefer an allowlist of hosts over a blocklist.
- Otherwise: allow `https` only. Resolve the hostname and reject private, loopback, link-local and unique-local ranges (IPv4 and IPv6). Connect to the IP you checked, so DNS can't change in between. Disable redirects, or re-check each hop.
- Cap response size and time. Check the content type.
- Never return fetch error text to the client. `connect ECONNREFUSED 10.0.0.5:80` turns the endpoint into a port scanner.
- Use a maintained library for the IP checks (`ssrf-req-filter` or `request-filtering-agent` for Node), not a hand-written regex.

## 10 · Dependencies

Keep dependencies patched. Run a vulnerability scanner (`npm audit`, `pip-audit`,
`bundler-audit`, Dependabot or Snyk) in CI, not manually and occasionally. Use widely used,
maintained libraries for auth, crypto and serialization.

## 11 · Done when

- Every external input is validated before use; every protected route checks authentication and resource-level authorization
- No secret is hardcoded, logged or committed (`git diff | grep -iE "key|token|secret|password"` comes back clean)
- Third-party tokens are verified (signature, `aud`, `iss`, `exp`); the tenant and user come only from the credential, and every query scopes by them
- Webhooks verify the raw body in constant time and dedupe by event ID
- Server-fetched URLs are allowlisted or IP-checked, size- and time-capped; no auth bypass can run on a deployed server
- Auth and expensive endpoints are rate-limited by identity, in a shared store
