---
name: frontend-build
description: Build React components, hooks, pages, forms, and UI features with correct state placement, server/client boundaries, composition, accessibility, and styling conventions. Use this whenever the user asks to create, add, build, scaffold, or "write me" a component, hook, page, layout, modal, table, form, or frontend feature — including small ones, and even when React isn't mentioned but the context is a JS/TS frontend project.
---

# Building frontend code

The target is code that looks like it came from someone who works in this
codebase every day, rather than something assembled from a tutorial.

**House rules.** The shared rules in the project instructions apply here —
verify before proposing, smallest change, no compliment openers, no closing
summaries. What follows is specific to building.

**See also.** If the code already exists and works and the ask is "tighten
this up" or "is this okay", that's `frontend-review`. Use this skill when
something new is being written, or when an existing component is being
replaced rather than patched.

## Step 1: Read the stack, don't assume it

This codebase could be any of several shapes: CRA or Vite with TypeScript and
either a styling framework or plain CSS; Next.js with Tailwind and some
styling or component library; or JavaScript without types. The correct answer
differs sharply between them.

Detect rather than guess. In order:

1. **`package.json`** — dependencies, versions, and scripts settle most of it. Ask for it if you don't have it.
2. **Existing imports and files** in what's been shared. They reveal the component library, the `cn()`/`clsx` helper, path aliases, and the file layout.
3. **One compact question**, only if the answer would change the shape of the code.

What actually matters:
- **Router shape** — Next.js App Router, Pages Router, or a client-side SPA router. Decides server/client components, data fetching, and whether `window` exists during render.
- **TypeScript or JavaScript** — don't hand a JS project annotated `.tsx`, and don't strip types from a TS project.
- **Styling** — Tailwind, CSS Modules, plain CSS, or a CSS-in-JS library. Reuse the project's tokens and helpers instead of inventing new ones.
- **Component library** — if shadcn/ui, Radix, MUI, Mantine, Chakra, Headless UI or similar is present, compose its primitives. Hand-rolling a `<Select>` or `<Dialog>` next to an existing library is the clearest tell of generated code.

## Step 2: Check versions before applying version-specific patterns

Framework conventions move faster than most people's mental model of them, and
a confidently-stated pattern from two majors ago is worse than an admission of
uncertainty. Read the installed majors from `package.json` before recommending
anything version-specific.

Things that have shifted and are easy to get wrong from memory:
- **Next.js** — fetch caching defaults, route segment config, whether `params`/`searchParams` are async, the caching directives and their APIs.
- **React** — the compiler (which changes memoisation advice entirely), `use()`, form actions and `useActionState`, ref as a plain prop.
- **Tailwind** — v4 moved configuration into CSS and reworked parts of the scale, so a `tailwind.config.js` answer is simply wrong there.
- **Routers and data libraries** — major versions rename and reshape APIs regularly.

When the installed version is newer than you can speak to confidently, say so
and check the current docs rather than filling the gap from memory.

## Step 3: Structural decisions

**Server vs client (App Router).** Default to a server component. Add
`'use client'` at the smallest leaf that needs interactivity, not at the top of
the tree. Functions and class instances can't cross the boundary.

**State placement**, in priority order:
1. Derive during render — if a value is computable from props or other state, compute it. Don't mirror props into state with an effect.
2. URL search params — filters, tabs, pagination, open panels. Survives refresh, shareable.
3. Local `useState` in the component that owns it.
4. Lift only to the nearest common ancestor that needs it.
5. Context or a store for genuinely cross-cutting state (auth, theme). Memoise the context value, or every consumer re-renders.

**Data fetching.** Server component: `await` directly. Client: the project's
data layer, typically TanStack Query. `useEffect` + `fetch` + three `useState`s
works as a demo but has no caching, no dedupe, and a race on fast navigation —
if an effect really is the right tool, include an `AbortController` or an
`ignore` flag.

**Effects** synchronise with things outside React: subscriptions, timers, DOM
measurement, non-React libraries. Not for transforming data, not for resetting
state on a prop change (use `key`), not for work that belongs in a handler.
Every subscription gets a cleanup.

**Props and composition.** Prefer `children` and slots over configuration
props. A fourth boolean prop usually means there are two components here.

**Forms.** Past three fields, use the project's form library or uncontrolled
inputs with `FormData`. Eight `useState` calls for eight inputs is a smell.

## Step 4: Non-negotiables

**Accessibility** is part of the component, not a follow-up pass:
- Native element first — `button`, `a`, `label`, `nav`, `dialog`. ARIA patches gaps in semantics; it doesn't replace them.
- Every input has an associated `label`. A placeholder is not a label.
- Anything clickable is keyboard-reachable with a visible focus ring.
- Dialogs and menus trap focus and restore it on close. This is why you use the library primitive.
- Icon-only buttons need an accessible name.

**Styling.** Use the project's scale tokens over arbitrary values unless the
design genuinely demands one. Conditional classes go through `cn()`/`clsx`
rather than inline ternary string concatenation. Repeated class strings become
a component.

**TypeScript.** No `any`. Explicit props type; inference for locals.
Discriminated unions beat optional-everything prop shapes.

## Step 5: What to avoid, concretely

- Comments restating the code. Comment non-obvious *why* only.
- Placeholder gaps: `// ... rest of your component`, `// your logic here`. Ship the file, or say which part you're showing.
- Scaffolding nobody asked for — try/catch everywhere, `?.` on values that can't be null, loading and error states on a static component.
- `useMemo`/`useCallback`/`React.memo` by default. They cost something; add them when there's a reason and name it. If the React Compiler is enabled, most manual memoisation is redundant.
- Premature abstraction: a `utils/` helper with one call site, a generic wrapper used once, a hook wrapping a single `useState`.
- Wrapper `div` soup. Use fragments; let the parent own layout.
- Inventing an API shape, env var, or design token that wasn't specified. Ask, or make the seam obvious and flag it in a line.
- Emoji in UI copy or code unless the project already uses them.

## Output

1. One or two lines: what you built, and any assumption you had to make.
2. The code — complete, runnable, in the project's language and layout.
3. Only if it's real: one note about a trade-off worth overriding.
