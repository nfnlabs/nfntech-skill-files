# Data fetching, caching and errors

Where data comes from, how long it's trusted, and what the user sees when
it fails. Check the router (App Router vs Pages vs SPA) and the installed
majors first — caching behaviour here is **version-dependent** and has
changed between Next.js majors.

## Choosing where to fetch

| Situation | Fetch in |
|---|---|
| Needed for first paint, same for many users or keyed by the session | Server Component: `await` directly, in parallel (`Promise.all`) when independent |
| User-driven, polled, optimistic, or shared across many client components | Client with TanStack Query (or the project's data layer) |
| Mutation from a form | Server Action or route handler, then revalidate (`forms.md`) |
| Pure SPA (Vite) | TanStack Query or the router's loader |

Don't mix idioms for one resource: pick one owner of each piece of data. A
raw `useEffect`+`fetch` is a last resort and needs abort, error and
loading handling. Server Actions are for **mutations**, not reads: the
framework queues them one at a time per client, so using one to fetch
data makes the page wait on its own requests.

## Parse at the boundary

A cast on `res.json()` is not validation. Define a schema per response
(zod/valibot), parse once in the fetcher, and let types flow from it. A
backend change then fails loudly in one place with a clear message, not as
`undefined is not a function` three components later. Throw a typed error
for non-2xx (`ApiError` with status and parsed body); `fetch` doesn't throw
on 404/500 by itself.

## Server caching and revalidation *(version-dependent)*

Never state a caching default from memory — read the installed Next.js
version's docs, because the defaults for `fetch`, route handlers and
dynamic APIs differ across majors.

Principles that hold regardless:

- Decide per resource: **static**, **time-based** (revalidate every N
  seconds), **tag/path-based on demand** (revalidate after a mutation), or
  **uncached** (per-user or must-be-live). Write the choice down in a
  comment next to the fetch.
- Per-user data must never land in a shared cache. Anything that reads
  `cookies()`/`headers()` or depends on the session is dynamic.
- After a mutation, revalidate by tag or path (`revalidateTag`,
  `revalidatePath`) in the same action; otherwise the user sees stale data
  and files a bug.
- Deduplicate within a request by wrapping a non-`fetch` data call
  (database, SDK) in React's `cache()`, or by calling the same `fetch`
  (which the framework memoises per request), rather than prop-drilling
  data.
- If the app seems "stuck" on old data in production but is fresh in dev,
  suspect caching first (`debug.md`).

## Client caching with TanStack Query

*(Version-dependent: examples are v5. v4 used `cacheTime` and `isLoading`
where v5 uses `gcTime` and `isPending`, and v5 requires the single-object
call signature. Read the installed major — SKILL.md §2.)*

- **Query keys are the cache's identity.** Build them from one factory per
  feature, hierarchical, with every input that changes the result:
  ```ts
  export const todoKeys = {
    all: ['todos'] as const,
    list: (filters: Filters) => [...todoKeys.all, 'list', filters] as const,
    detail: (id: string) => [...todoKeys.all, 'detail', id] as const,
  }
  ```
  A key missing a variable returns the wrong data; a key with an unstable
  object identity isn't a problem (keys hash structurally), but a key that
  includes volatile values (timestamps) never caches.
- **Invalidate after mutation** by the narrowest prefix that covers what
  changed: `queryClient.invalidateQueries({ queryKey: todoKeys.all })`
  after create, `todoKeys.detail(id)` after an edit. Don't `invalidate()`
  everything, and don't hand-edit the cache unless doing an optimistic
  update with rollback in `onError`/`onSettled`.
- `staleTime` is the main tuning knob: the default of 0 refetches on every
  mount and focus. Set it per query from how fresh the data must be.
- Don't copy query data into `useState`; derive from it.
- Keep `enabled` for dependent queries, `select` for derived slices, and
  server-prefetch + hydrate (`HydrationBoundary`) when a Server Component
  can seed the cache.
- Set a global retry policy: don't retry 4xx (they won't succeed), cap 5xx
  retries, and use backoff.

## Errors: where each kind goes

| Error | Handled by |
|---|---|
| Expected, per-operation (validation 422, "email taken") | Return it as data (`{ ok: false, error }`) or a typed error and show it inline next to the cause |
| Unexpected render/fetch failure in a route segment | `error.tsx` for that segment (App Router) — a Client Component with a `reset()` retry; `global-error.tsx` for the root layout |
| Unexpected failure in a subtree of a client app | An error boundary around it (`react-error-boundary`), placed so the rest of the page keeps working |
| Missing resource | `notFound()` + `not-found.tsx`, not an error |
| Event handlers, async code, effects | **Not caught by boundaries** — use `try/catch`, or a mutation's `onError`. For queries, read `error` from the hook, set `throwOnError` to hand it to an error boundary, or use the global `QueryCache` `onError` *(v5 removed `onError` from `useQuery`; v4 still has it)* |

- Boundaries go at meaningful seams (route, widget, list item), not one
  at the root only and not around every component.
- Every boundary offers recovery: retry, or a way back. An error screen
  with no action is a dead end.
- Don't show raw messages or stack traces; show a human sentence, and log
  the detail with a request/trace id to the error tracker (Sentry etc.),
  scrubbed of PII and tokens.
- In `error.tsx` in production, Next hides server error details by design
  (it gives a digest); look the digest up in server logs.
- `error.tsx` limits *(version-dependent — verify against the installed
  Next.js docs)*: a segment's `error.tsx` does not catch errors thrown by
  the layout in the same segment (put the boundary one level up), and
  `global-error.tsx` replaces the root layout, so it must render its own
  `<html>` and `<body>`.
- Never swallow: a `catch` that logs and continues turns a failure into a
  blank screen.

## The four states

Anything that fetches renders **loading, empty, error and success** — each
designed, none implied. Loading uses `loading.tsx`/Suspense fallbacks or
skeletons sized to the content to avoid layout shift. Empty explains what
to do next. Error offers retry. Don't leave "success with zero results"
indistinguishable from "failed".

## Working rules specific to data

- Show the cache decision (static/time/on-demand/none) in the code or the
  answer, not as an unstated default.
- Don't introduce TanStack Query into a codebase standardised on something
  else — match it.
- One resource, one fetcher, one key factory.
- Mutations always say what they revalidate.
