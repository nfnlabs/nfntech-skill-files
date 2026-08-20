---
name: frontend-perf
description: Diagnose and fix React/Next.js performance problems — slow page loads, poor LCP/INP/CLS, janky interactions, unnecessary re-renders, oversized bundles, slow lists and tables. Use this whenever the user says something is slow, laggy, janky, freezing, or heavy, asks about bundle size, Lighthouse or Core Web Vitals, re-render counts, memoization, virtualization, code splitting, or asks how to "optimize" or "speed up" a page or component.
---

# Frontend performance

Most performance advice circulates as folklore applied without measurement.
The discipline: **find the number, find the cause, change one thing, check the
number again.**

**House rules.** The shared rules in the project instructions apply — verify
before proposing, smallest change, no compliment openers, no closing
summaries. What follows is specific to performance.

**See also.** If "slow" turns out to be a hang, an infinite retry, a request
loop, or something that never completes, that's a bug rather than a
performance problem — switch to `frontend-debug`.

## Step 1: Get a measurement first

Before proposing changes, establish what's actually slow:

- **Which metric?** Load (LCP, TTFB, bundle size) and interaction (INP, dropped frames) share almost no causes or fixes.
- **A number.** "Feels slow" isn't actionable. A Lighthouse run, a Profiler flame chart, a bundle report, or a stopwatch on one interaction.
- **Where.** Dev server or production build? Dev numbers are meaningless for this — never optimise against them.
- **On what.** Throttled mobile CPU and network, or a fast laptop on fibre?

With no measurement available, the first response is how to get one:

| Symptom | Tool |
|---|---|
| Slow first load | Lighthouse against a production build, incognito; Network waterfall |
| Slow interaction, typing lag | React DevTools Profiler; Performance panel long tasks |
| "The bundle is huge" | Route output from the production build, `@next/bundle-analyzer`, or `rollup-plugin-visualizer` |
| Layout jumping | Lighthouse CLS; layout shift markers in the Performance panel |

## Step 2: Check versions before applying fixes

Caching and data-fetching defaults change across major versions, and a fix
aimed at the wrong major can be a no-op or a regression. Read the installed
versions from `package.json` first.

Particularly worth confirming:
- **Next.js** — whether `fetch` is cached by default, route segment config options, the current caching directives and their names, image component defaults.
- **React** — whether the compiler is enabled, since that changes the memoisation section below almost entirely.
- **Build tooling** — chunking and tree-shaking behaviour differs enough between bundler majors to matter for bundle advice.

If the installed version is newer than you can speak to confidently, say so
and check current docs rather than applying the pattern you remember.

## Step 3: Route by symptom

### Slow load / poor LCP

Roughly in order of typical impact:

1. **Images.** Unsized, unoptimised, wrong format, or lazy-loaded when it's the LCP element. Real dimensions, modern formats, priority on the hero.
2. **JavaScript shipped.** Check the route's client bundle. Common bloat: an icon set imported as a namespace, a date or utility library imported wholesale, an editor or charting library on a page that doesn't show it above the fold, duplicated dependency versions.
3. **Server/client split.** A `'use client'` at the top of a page pulls the whole subtree into the client bundle. Push the boundary down to interactive leaves.
4. **Code splitting.** Dynamic import for modals, editors, charts, maps — anything absent from first paint.
5. **Waterfalls.** Sequential awaits that could be `Promise.all`; client fetches that only start after hydration; render-blocking stylesheets.
6. **Fonts.** Self-hosted or framework-managed, `font-display: swap`, preloaded. Avoid a blocking third-party font request.
7. **Third-party scripts.** Analytics, chat widgets, tag managers — defer or lazy-load.

### Slow interaction / poor INP

1. **Profile first.** The Profiler shows which components rendered and why. Guessing here is how people memoise the wrong thing.
2. **Re-render causes**, by frequency: a context value recreated each render, state held too high in the tree, a fresh object/array/inline function passed to a memoised child, a store subscription without a scoped selector.
3. **Fix the cause before memoising.** Moving state down or splitting a context usually beats wrapping ten components in `React.memo`.
4. **Long lists.** Past a few hundred rows, virtualise. No amount of memoisation rescues 5,000 DOM nodes.
5. **Main-thread work.** Debounce or throttle input handlers, `useDeferredValue` for a heavy derived view, `useTransition` for non-urgent updates, a worker for genuinely heavy computation.
6. **Layout thrash.** Reading `offsetHeight`/`getBoundingClientRect` in a loop that also writes styles.

### Layout shift

Reserve space: explicit image dimensions, `min-height` on async content,
nothing injected above existing content after load, font metrics matched to
avoid a swap jump.

## Step 4: Memoisation policy

This is where generic advice does the most damage, so be explicit:

- `useMemo`/`useCallback`/`React.memo` aren't free — allocation, comparison cost, and reading overhead.
- Add them when a profiler shows measurable cost, a computation is genuinely expensive, a value feeds an effect's dependencies or a memoised child, or a context value would otherwise be recreated.
- Skip them for primitives, cheap components, and blanket "best practice" application.
- **Confirm whether the React Compiler is enabled first.** If it is, most manual memoisation is redundant and adds noise.

## Step 5: Report the result

State each recommendation as *baseline → change → expected or measured
result*. When impact can't be estimated, say so and rank by confidence.

Change one thing at a time so attribution is real.

## Working rules

- No generic checklists. Respond to this page, this component, this measurement — not "10 tips to speed up React".
- Prefer a bounded fix to a rewrite. If the architecture really is the problem, say so in a paragraph with the specific cost and let the user decide.
- Don't stack five changes and claim a combined improvement.
- Say when something isn't worth optimising. Shaving 4ms off a once-per-session render is worth less than the sentence explaining why not.
- Dev-mode timings are not evidence.
