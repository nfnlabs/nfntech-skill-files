# Frontend security

The browser is hostile territory: anything shipped to it is readable, and
anything it sends is forgeable. Frontend checks are UX, never enforcement —
the server must decide. Server-side API security is in
`backend-engineering` (`companions/security.md`); this file covers what the
React/Next.js layer owns.

## Token storage and sessions

| Option | Verdict |
|---|---|
| `httpOnly`, `Secure`, `SameSite=Lax` (or `Strict`) cookie set by the server | **Default.** JavaScript can't read it, so XSS can't exfiltrate it. |
| Access token in `localStorage` / `sessionStorage` | Avoid. Any XSS, including from a compromised npm dependency, reads it. |
| Access token in JS memory, refresh token in an `httpOnly` cookie | Acceptable where a separate API origin makes cookies awkward; re-fetch on reload. |

- Never put a JWT or session id in a URL, a log, an analytics event, or
  `NEXT_PUBLIC_` config.
- Cookie flags: `httpOnly`, `Secure`, a sensible `SameSite`, scoped
  `Path`/`Domain`, a bounded lifetime. Logout clears server-side too.
- Decoding a JWT in the client to show a name is fine; trusting its claims
  for authorisation is not.
- Don't persist authenticated query data to `localStorage` or a
  service-worker cache (`persistQueryClient`, offline caches). If you
  must, scope it to the session, exclude sensitive queries, and clear it
  on logout.

## CSRF

Cookie-based auth means the browser attaches credentials to cross-site
requests, so state-changing requests need protection:

- `SameSite=Lax` or `Strict` blocks most cross-site POSTs, but is not
  sufficient alone (subdomain attacks, legacy browsers, `GET` that
  mutates).
- Add a CSRF token (double-submit or synchroniser) or require a custom
  header that a cross-origin form can't send, checked on the server.
- Never mutate on `GET`. Bearer-token-in-header APIs aren't CSRF-prone but
  bring the storage problem above.
- Cookies for a *cross-site* API need `SameSite=None; Secure`, which
  removes the SameSite protection — keep the CSRF token and an
  `Origin`/`Referer` check in that case.
- Next.js Server Actions check that `Origin` matches `Host` by default
  *(version-dependent)* — don't weaken `allowedOrigins`, and don't treat it
  as complete protection.

## Server Actions and route handlers are public endpoints

A Server Action is an HTTP `POST` endpoint with a generated URL. Hiding the
button hides nothing. In every action and route handler that acts on a
user's behalf — everything except *deliberately public* endpoints such as
signup, login, password reset, contact forms and webhooks (those instead
need steps 3 and 4, rate limiting, and generic error messages; see
"Authentication itself" below):

1. Authenticate: read the session on the server, inside the action.
2. Authorise: check this user may touch this resource (ownership, role) —
   not merely that they're logged in.
3. Validate input with a schema (`forms.md`); the arguments are untrusted
   even though they came from your own form.
4. Return only what the caller may see; no whole database rows.

Auth done only in middleware (`middleware.ts`, renamed `proxy.ts` in
Next.js 16 — version-dependent) or a layout isn't enough — layouts don't
re-run on every action call, and middleware-only authorisation has been
bypassed in published Next.js vulnerabilities (check the advisories for
the installed version). Put the check in a shared helper
(`requireUser()`) and call it first, every time, in the data-access layer
too.

## Authentication itself

- Don't hand-roll authentication, session handling, password hashing or
  crypto. Use the project's library or provider (Auth.js, Clerk, a
  provider SDK, the backend's own auth) and follow its documented flow.
- Public login, signup and reset actions need: rate limiting per account
  and per IP, constant-shape generic errors ("Email or password is
  incorrect", never "no such user" — that enumerates accounts), no
  secrets or tokens echoed back in the response, and a password rule
  that matches the backend's.
- Prefer the `__Host-` cookie name prefix for session cookies where the
  library allows it (forces `Secure`, `Path=/`, no `Domain`).
- Server-side rate limiting and credential storage belong to the backend;
  see `backend-engineering` `companions/security.md`.

## Server-only code and secrets

- `import 'server-only'` at the top of any module that touches secrets, the
  database, or server config; importing it from a Client Component then
  fails the build instead of leaking.
- Secrets live in server environment variables only. **Any variable
  prefixed `NEXT_PUBLIC_` or `VITE_` is inlined into the client bundle at
  build time and visible to everyone** — API keys, signing secrets and
  database URLs must never carry the prefix. "Public" keys (a Maps key, an
  analytics id, a Stripe publishable key) are fine, restricted by domain
  where the vendor allows.
- Don't pass whole server objects as props to Client Components: props
  serialise into the HTML. Select the fields needed.
- Rotate anything that was ever committed or shipped in a bundle; deleting
  the commit doesn't un-leak it. Check built output
  (`grep` the `.next/static` or `dist` folder) when in doubt.

## XSS

- React escapes interpolated text. The risks are the escape hatches:
  `dangerouslySetInnerHTML` (sanitise with DOMPurify and a strict
  allow-list; on the server it needs a DOM implementation, e.g.
  `isomorphic-dompurify`, so verify the setup works in the runtime in
  use), `href`/`src` from user input (allow-list `http:`/`https:`/
  `mailto:`; reject `javascript:`), and `innerHTML` or `eval` anywhere.
- Rendering Markdown or CMS HTML: sanitise after conversion, not before.
- Don't build `<script>` content or inline JSON from user data without
  escaping `<`; use the framework's mechanism.
- Third-party scripts run with your page's full authority. Fewer is
  better; load from your origin or with Subresource Integrity; audit new
  dependencies and lock files.

## Content Security Policy and headers

- Ship a CSP, starting in report-only mode, then enforce. Prefer nonce- or
  hash-based `script-src` with `'strict-dynamic'` over `'unsafe-inline'`.
  In Next.js, nonces need dynamic rendering *(version-dependent)* — check
  the installed major's CSP guidance.
- Also set `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin`,
  `frame-ancestors` (or `X-Frame-Options`) against clickjacking,
  `Strict-Transport-Security`, and a restrictive `Permissions-Policy`.
- Configure these in `next.config`/the host, not per page.
- Don't serve production source maps publicly unless you intend to expose
  your source; upload them to the error tracker instead.

## Open redirects and navigation

- Never `redirect(searchParams.next)` or `router.push(url)` with an
  unchecked user-supplied target. Accept only same-origin relative paths:
  must start with a single `/`, not `//` or `/\`, and parse to your own
  origin; otherwise fall back to a default.
- OAuth `redirect_uri` is allow-listed on the provider, exact-match.
- `target="_blank"` links: `rel="noopener noreferrer"`.

## Server-side fetches of user-supplied URLs (SSRF)

A Server Component, Server Action or route handler that calls
`fetch(userUrl)` lets an attacker make your server request internal
addresses (cloud metadata, `localhost`, private ranges).

- Don't fetch arbitrary user-supplied URLs. If you must (link previews,
  webhooks, image proxies), allow-list hosts, require `https:`, resolve
  the hostname and reject loopback, link-local and private IP ranges,
  disable or re-validate redirects, and set a timeout and size cap.
- Image optimisation `remotePatterns` is an allow-list; keep it exact, not
  `**`.

## Dependencies and supply chain

- Before recommending or adding any package, check it against the
  registry: `npm view <pkg> version deprecated peerDependencies`, and
  confirm it is maintained (recent release) and compatible with the
  installed React, Next.js, TypeScript and ESLint majors. Never invent a
  package name or a version from memory; if you can't check, say so.
- Run `npm audit` (or the project's equivalent) after any dependency
  change and in CI. Fix or consciously accept each finding; "zero
  vulnerabilities" is a point-in-time result, not a permanent property.
- Commit the lockfile and install with `npm ci` / `pnpm install
  --frozen-lockfile` in CI.
- Review new packages (maintainers, download history, postinstall
  scripts) before adding; prefer fewer dependencies.
- Pin versions for anything that runs at build time with access to
  secrets; enable automated vulnerability alerts.

## Other checks

- `postMessage`: verify `event.origin`; specify the target origin when
  sending.
- File upload: validate type and size on the server; don't trust the
  `Content-Type` or extension from the client.
- CORS is a browser-side protection for the *user*, not an access control;
  never answer it with `*` plus credentials.
- Don't render raw error messages or stack traces from the server to users.
- `npm audit` / dependency review in CI; pin and review postinstall
  scripts of new packages.

## Review output

Per finding: where, the attack in one sentence ("an attacker who can set
`?next=` sends users to a phishing site after login"), and the concrete
replacement. Rank real exploitability above theoretical; say when
something is fine. A hardcoded secret or an action without an auth check
is **Blocking**.
