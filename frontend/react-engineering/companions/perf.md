# Frontend performance

Most performance advice circulates as folklore applied without
measurement. The discipline: **find the number, find the cause, change
one thing, check the number again.**

## Step 1: Get a measurement first

Before proposing changes, establish what's actually slow:

- **Which metric?** Load (LCP, TTFB, bundle size) and interaction (INP,
  dropped frames) share almost no causes or fixes.
- **A number.** "Feels slow" isn't actionable. A Lighthouse run, a
  Profiler flame chart, a bundle report, or a stopwatch on one interaction.
- **Where.** Dev server or production build? Dev numbers are meaningless
  for this — never optimise against them.
- **On what.** Throttled mobile CPU and network, or a fast laptop on fibre?

With no measurement available, the first response is how to get one:

| Symptom | Tool |
|---|---|
| Slow first load | Lighthouse against a production build, incognito; Network waterfall |
| Slow interaction, typing lag | React DevTools Profiler; Performance panel long tasks |
| "The bundle is huge" | Route output from the production build, plus an analyzer for the toolchain in use — `@next/bundle-analyzer` or the framework's built-in analyzer on Next.js, `rollup-plugin-visualizer` on Vite *(tooling is version-dependent; check what the installed major ships)* |
| Layout jumping | Lighthouse CLS; layout shift markers in the Performance panel |

## Step 2: Route by symptom

### Slow load / poor LCP

Roughly in order of typical impact:

1. **Images.** Unsized, unoptimised, wrong format, or lazy-loaded when
   it's the LCP element. Real dimensions, modern formats, priority on
   the hero, and `sizes`/`srcset` so phones don't download
   desktop-sized images. *(How to mark the LCP image is version-dependent:
   `priority` on `next/image` in older Next.js, `preload` /
   `fetchPriority="high"` in newer ones — check the installed major
   before naming a prop.)*
2. **JavaScript shipped.** Check the route's client bundle. Common
   bloat: an icon set imported as a namespace, a date or utility library
   imported wholesale, an editor or charting library on a page that
   doesn't show it above the fold, duplicated dependency versions.
3. **Server/client split.** A `'use client'` at the top of a page pulls
   the whole subtree into the client bundle. Push the boundary down to
   interactive leaves.
4. **Code splitting.** Dynamic import for modals, editors, charts, maps —
   anything absent from first paint. Wrap slow Server Component data in
   `<Suspense>` boundaries sized to the slow part (and `loading.tsx` per
   route segment) so the shell streams instead of blocking on the
   slowest fetch.
5. **Waterfalls.** Sequential awaits that could be `Promise.all`; client
   fetches that only start after hydration; render-blocking stylesheets.
6. **Fonts.** Self-hosted or framework-managed, `font-display: swap`,
   preloaded. Avoid a blocking third-party font request.
7. **Third-party scripts.** Analytics, chat widgets, tag managers — defer
   or lazy-load (`next/script` with `afterInteractive` or `lazyOnload` on
   Next.js; `async`/`defer` elsewhere).
8. **Barrel files.** An `index.ts` re-exporting a whole feature or icon
   set can pull unused code (and server-only code) into the route's
   bundle; import by file path (`foundation.md` barrel rule).

### Slow interaction / poor INP

1. **Profile first.** The Profiler shows which components rendered and
   why. Guessing here is how people memoise the wrong thing.
2. **Re-render causes**, by frequency: a context value recreated each
   render, state held too high in the tree, a fresh object/array/inline
   function passed to a memoised child, a store subscription without a
   scoped selector.
3. **Fix the cause before memoising.** Moving state down or splitting a
   context usually beats wrapping ten components in `React.memo`.
4. **Long lists.** Past a few hundred rows, virtualise (TanStack Virtual,
   react-window or the project's existing choice). No amount of
   memoisation rescues 5,000 DOM nodes.
5. **Main-thread work.** Debounce or throttle input handlers,
   `useDeferredValue` for a heavy derived view, `useTransition` for
   non-urgent updates, a worker for genuinely heavy computation.
6. **Layout thrash.** Reading `offsetHeight`/`getBoundingClientRect` in a
   loop that also writes styles.

### Layout shift

Reserve space: explicit image dimensions, `min-height` on async content,
nothing injected above existing content after load, font metrics matched
to avoid a swap jump.

## Step 3: Memoisation policy

This is where generic advice does the most damage, so be explicit:

- `useMemo`/`useCallback`/`React.memo` aren't free — allocation,
  comparison cost, and reading overhead.
- The rule, including the compiler on/off split, is stated once in
  SKILL.md §5 — apply that, and don't restate or contradict it here.
- In a perf answer, name the profiler evidence for every `memo`,
  `useMemo` or `useCallback` you recommend, and skip them for primitives,
  cheap components and blanket "best practice" application.

## Step 4: Report the result

State each recommendation as *baseline → change → expected or measured
result*. When impact can't be estimated, say so and rank by confidence.
Change one thing at a time so attribution is real.

## Working rules specific to perf

- No generic checklists. Respond to this page, this component, this
  measurement — not "10 tips to speed up React".
- Prefer a bounded fix to a rewrite. If the architecture really is the
  problem, say so in a paragraph with the specific cost and let the user
  decide.
- Don't stack five changes and claim a combined improvement.
- Say when something isn't worth optimising. Shaving 4ms off a
  once-per-session render is worth less than the sentence explaining why not.
- Dev-mode timings are not evidence.
