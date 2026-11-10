# Building frontend code

The target is code that looks like it came from someone who works in this
codebase every day, rather than something assembled from a tutorial.

Before writing: SKILL.md §2 has been run (framework, router, TypeScript,
React Compiler, styling helper, data layer, form/test stack), and you have
found one existing feature of the same kind to copy the shape of. For a
whole feature, follow the build order in `foundation.md`; for a form, a
fetch, auth, or tests, open the companion that owns it rather than
improvising here.

## Structural decisions

**Server or client first.** In the App Router, start every component as a
Server Component. Add `'use client'` only at the leaf that needs state,
effects, browser APIs or event handlers, and keep the leaf small so the
rest stays on the server. Pass server data down as serialisable props;
don't pass whole server objects (`security.md`).

**Props and composition.** Prefer `children` and slots over configuration
props. A fourth boolean prop usually means there are two components here.
Use discriminated unions when props are mutually exclusive:

```ts
type ButtonProps =
  | { href: string; onClick?: never }
  | { href?: never; onClick: () => void }
```

Extend native element props (`ComponentProps<'button'>`) and spread the rest
so `aria-*`, `className` and `ref` pass through. `ref` is a plain prop in
React 19 *(version-dependent — `forwardRef` on older majors)*.

**State.** Follow the priority in SKILL.md §5: derive → URL → local →
lift → shared store. Filters, tabs, sort and pagination belong in the URL
so they survive reload and can be shared. Reach for a state library only
when state is genuinely cross-cutting; match the one already in the repo.

**Custom hooks.** Extract a hook when the logic is reused or when it has
real behaviour (subscription, debounce, measurement) — not to wrap a lone
`useState`. A hook returns what callers use, with a stable shape.

**Forms.** Past three fields, use the project's form library or
uncontrolled inputs with `FormData`; one schema shared with the server —
see `forms.md`. Eight `useState` calls for eight inputs is a smell.

**Data.** Fetch on the server where possible; on the client, use the
project's data layer with a typed, schema-parsed fetcher — see
`data-and-errors.md`. Never `useEffect`+`fetch` by default.

**Styling.** Use the project's scale tokens over arbitrary values unless
the design genuinely demands one. Conditional classes go through
`cn()`/`clsx` rather than inline ternary string concatenation. Repeated
class strings become a component. Compose the existing component library
(shadcn/ui, Radix, MUI…) before hand-rolling a primitive. For a modal use
native `<dialog>` or the library's dialog; for menus, comboboxes and
tooltips use the library — never a custom `div` version, because the
focus and keyboard handling is the hard part.

**Visual design.** Generic output is a defect. In an existing project, use
its tokens, spacing scale and components and look at two existing screens
first. With no design system, define a small scale up front: a spacing
scale (4/8px steps), a type scale with one or two families, a neutral
palette plus one accent that meets contrast (SKILL.md §5), a radius and
shadow set, and all interactive states — default, hover, focus-visible,
active, disabled, loading, error. Provide dark mode if the project does
(`prefers-color-scheme` or the existing theme mechanism). Design mobile
first with real breakpoints, test at 320px, and design the empty, loading
and error states as deliberately as the filled one. Use real copy, not
lorem ipsum, routed through the project's i18n messages when it has any, and keep motion short and respectful of
`prefers-reduced-motion`.

**Client state libraries.** Match the one in the repo. For a new project,
default to no library (SKILL.md §5 priority), then Zustand or Jotai for
small shared client state, and Redux Toolkit only when the team already
knows it or needs its devtools and middleware at scale. Server data is not
client state: it belongs to the data layer (`data-and-errors.md`), not a
store. Select narrowly (`useStore(s => s.x)`) so unrelated updates don't
re-render.

**Routing.** Use the framework's router: file-based routes in Next.js, the
project's React Router / TanStack Router config otherwise. Keep route
files thin, validate path and search params with a schema before use,
use `Link` for navigation, and keep filter and pagination state in the
URL. Don't add a second router.

**Metadata and SEO** (public pages). In Next.js set `metadata` or
`generateMetadata` per route: a unique `title` and `description`,
canonical URL, Open Graph and Twitter images, plus `robots`, a sitemap and
`robots.txt` at the app level. One `h1` per page, descriptive link text,
real `alt`. Structured data (JSON-LD) only where it is true. Authenticated
pages are usually `noindex`.

**Every fetching component has four states.** Loading, empty, error,
success — designed, with skeletons that match the final layout to avoid
layout shift. A static component needs none of them.

**Accessibility while building**, not after: native element first, a label
per input, a visible focus ring, an accessible name on icon-only controls,
keyboard path for everything clickable, focus managed on dialog
open/close, and heading levels that don't skip. Check by tabbing through
the result. Also: landmarks (`header`, `nav`, `main`, `footer`) and a
skip-to-content link; **no ARIA is better than wrong ARIA** — add `role`
or `aria-*` only where no native element does the job, never redundant
(`<button role="button">`), and never `aria-hidden` on something
focusable; `aria-live` for async status messages. In a client-routed app,
each route change updates the document title and moves focus (to the new
`h1` or the main region) — the Next.js App Router does part of this, so
check rather than assume.

**Images, links and media.** Use the framework's image component with real
`width`/`height` (or `fill` with a sized parent) and meaningful `alt`
(empty `alt` for decorative). Use the router's `Link` for internal
navigation and a real `<a>` otherwise. Lazy-load below the fold only.

**Types.** Props typed explicitly at the component boundary; no `any`;
external data parsed, not cast. Export a type only if something imports it.

**Files.** One component per file, named after it; colocate its test and
styles; follow the barrel rule in `foundation.md` (types and client-safe
exports only; import server code by file path). Match the repo's naming
(kebab-case vs PascalCase files).

## What to avoid, concretely

- Comments restating the code. Comment non-obvious *why* only.
- Placeholder gaps: `// ... rest of your component`, `// your logic here`.
  Ship the file, or say which part you're showing.
- Scaffolding nobody asked for — try/catch everywhere, `?.` on values that
  can't be null, loading and error states on a static component.
- `useMemo`/`useCallback`/`React.memo` by default — follow the memoisation
  rule in SKILL.md §5 and name the reason when you add one.
- Premature abstraction: a `utils/` helper with one call site, a generic
  wrapper used once, a hook wrapping a single `useState`.
- Wrapper `div` soup. Use fragments; let the parent own layout.
- `useEffect` to derive data, to reset state on a prop change (use `key`),
  or to run something that belongs in an event handler.
- Index as `key` in a list that can reorder, filter or delete.
- `'use client'` at the top of a page "to make the error go away".
- Inventing an API shape, env var, or design token that wasn't specified.
  Ask, or make the seam obvious and flag it in a line.
- A secret in a public-prefix variable (SKILL.md §5), or a mutation with
  no server-side auth check (`security.md`).
- Emoji in UI copy or code unless the project already uses them.

## Completion checklist

Before saying done, confirm and, if you can't, say which you skipped:

- Runs through the project's `typecheck` and `lint` scripts clean.
- Uses an existing pattern from the repo, named in the answer.
- All four states handled (if it fetches); keyboard-only path works.
- A test exists for the behaviour (`testing.md`) — or you state that none
  was added.
- If it mutates data: `security.md` has been applied (auth, authorisation,
  validation in the action itself).
- No new dependency without saying why the existing stack couldn't do it.
- Anything deliberately left out or assumed is listed.

## Output

1. One or two lines: what you built, which existing pattern you matched,
   and any assumption you had to make.
2. The code — complete, runnable, in the project's language and layout.
3. Only if it's real: one note about a trade-off worth overriding.
