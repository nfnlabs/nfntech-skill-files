---
name: frontend
description: Build, review, debug, or optimize React, Next.js, TypeScript, and JavaScript frontend code. Use this whenever the user pastes code and asks "what do you think"/"review this"/"clean this up"; asks to create, add, build, scaffold, or "write me" a component, hook, page, layout, modal, table, form, or frontend feature; reports something broken, pastes an error or stack trace, says code "isn't working" or "throws"; or says something is slow, laggy, janky, asks about bundle size, Core Web Vitals, re-renders, memoization, or "optimize"/"speed up". Covers small snippets too.
---

# Frontend engineering

Read the codebase before advising it, then open exactly one companion.
Loading all four for one change buries the answer under context that
doesn't apply. An existing convention outranks anything written in these
companions — where the codebase and a companion disagree, the codebase
wins and you say so.

## 1 · Route by task

| The task | Open |
|---|---|
| Something new is being written, or an existing component is being replaced rather than patched | `companions/build.md` |
| Existing code that works, and the ask is "tighten this up", "is this okay", feedback on a PR/component/hook | `companions/review.md` |
| Something is slow, laggy, janky, freezing, or heavy; bundle size, Core Web Vitals, re-renders, memoisation, virtualization, code splitting | `companions/perf.md` |
| Something is broken: an error, a stack trace, "won't render", "logs undefined", dev/production behaviour differs | `companions/debug.md` |

One companion, occasionally two — a compound ask ("clean this up and it's
laggy too") can legitimately open both. Don't open a third to be thorough.

**Ambiguous "refactor this" / "clean this up".** Decide before opening
anything: if the existing structure broadly survives, that's `review.md`;
if the honest answer is a new implementation, that's `build.md`. State
which reading you took in one line and proceed — don't ask.

**Ambiguous "slow".** If it turns out to be a hang, an infinite retry, or
something that never completes, that's `debug.md`, not `perf.md`. Correct
but slow is perf; wrong is debug.

## 2 · Read the project first

Never skip this on a codebase that already exists — every companion's
advice is a comparison against what's there.

```
cat package.json                                    # deps, versions, scripts
ls next.config.* vite.config.* remix.config.* 2>/dev/null   # framework + router shape
ls CLAUDE.md AGENTS.md .cursorrules 2>/dev/null      # binding; outranks these files
grep -rl "cn(\|clsx(" src app 2>/dev/null | head      # styling helper in use
grep -rl "@tanstack/react-query\|swr" package.json 2>/dev/null  # client data layer
```

Then: existing imports and files already shared in the conversation —
they reveal the component library, path aliases, and file layout better
than any config file. Ask **one compact question** only if the answer
would change the shape of the code or the diagnosis.

What actually matters: router shape (decides server/client split, data
fetching, whether `window` exists during render), TypeScript or
JavaScript, styling system, and whether a component library (shadcn/ui,
Radix, MUI, Mantine, Chakra, Headless UI) is present to compose against
instead of hand-rolling.

## 3 · Established codebase or new ground?

| Signal | Then |
|---|---|
| A working app with existing patterns for this kind of thing | Match the existing convention — state idiom, file layout, error handling, styling helper — even where it's not what you'd choose fresh. |
| Empty project, or the first component/feature of its kind in the repo | You choose the default — pick current, well-supported patterns and say which you picked and why. |
| A pattern that looks accidental (no error boundary, inconsistent naming, untyped fetches) | Don't "fix" it silently mid-task. Ask, or flag it as a separate note — it may be deliberate. |

The distinction matters because the same advice flips sign: "use the
project's data layer" is a sound default in an empty app and, in a
codebase already standardised on something else, a proposal to introduce
a second idiom — worse than either alone.

## 4 · Version currency

Framework conventions move faster than most people's mental model of them.
A confidently-stated pattern from two majors ago costs more trust than an
admission of uncertainty. Read the installed majors from `package.json`
before flagging, fixing, or building anything version-specific.

Things that have shifted and are easy to get wrong from memory:
- **Next.js** — fetch caching defaults, route segment config, whether
  `params`/`searchParams` are async, current caching directive names,
  image component defaults.
- **React** — the compiler (changes memoisation advice almost entirely),
  `use()`, form actions and `useActionState`, ref as a plain prop.
- **Tailwind** — v4 moved configuration into CSS; a `tailwind.config.js`
  answer is simply wrong there.
- **Routers and data libraries** — major versions rename and reshape APIs
  regularly.

When the installed version is newer than you can speak to confidently,
say so and check current docs rather than filling the gap from memory.

## 5 · Invariants

These hold across all four companions, so they're stated once. A change
or finding that breaks one is wrong even when it compiles and tests pass.

- **State**, in priority order: derive during render → URL search params
  (filters, tabs, pagination) → local `useState` → lift only as far as
  needed → context/store only for genuinely cross-cutting state, value
  memoised.
- **Effects** synchronise with things outside React — subscriptions,
  timers, DOM measurement, non-React libraries. Not for transforming
  data, not for resetting state on a prop change (`key` instead), not for
  work that belongs in a handler. Every subscription gets cleanup.
- **Accessibility is not a follow-up pass.** Native element first
  (`button`, `a`, `label`, `nav`, `dialog`). Every input has an associated
  label. Anything clickable is keyboard-reachable with a visible focus
  ring. Dialogs/menus trap and restore focus. Icon-only controls get an
  accessible name.
- **Server/client boundary.** `'use client'` at the smallest leaf that
  needs it, not the top of the tree. Nothing server-only (env vars, API
  keys, server config) reachable from the client bundle.
- **Types.** No `any`. Discriminated unions over optional-everything
  props. A cast on `fetch().json()` is a lie the type system repeats back.
- **Data fetching.** Server component: `await` directly. Client: the
  project's data layer (typically TanStack Query). A raw
  `useEffect`+`fetch` needs an `AbortController` or `ignore` flag if it's
  really the right tool.

## 6 · Working rules (all companions)

- Verify before proposing — read the actual code/config, don't assume.
- Smallest change that solves the problem. Don't rewrite the file, don't
  refactor mid-task, don't drive-by rename or reformat unrelated code.
- No opening compliment, no restating what the code does, no closing
  summary table repeating what was just said.
- Ask only what the code can't answer for itself — the stack, the
  convention, the reproduction. Everything else is visible in the repo or
  has a defensible default.
- Say which companion you followed and, on an existing codebase, which
  existing feature/pattern you matched — makes a wrong route cheap to
  correct.
- Finish with the project's typecheck/lint (`tsc --noEmit`, `next lint`,
  or whatever `package.json` defines) before calling it done, and name
  anything you deliberately left undone.
