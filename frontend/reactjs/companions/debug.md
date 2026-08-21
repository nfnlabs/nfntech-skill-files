# Debugging frontend issues

The failure mode worth avoiding is confident guessing: three plausible
fixes, all applied, none verified. That leaves two pieces of cargo cult
behind and a bug that comes back.

Work as a hypothesis loop: **observe → hypothesise → predict → test → narrow.**

## Step 0: The fast path

If the pasted evidence already contains the answer — a one-line error
with the offending line visible, a signature from the table below that
matches unambiguously — just say what's wrong and fix it. Don't run the
evidence checklist as ceremony. Asking for a reproduction of a missing
dependency array is worse than useless.

The checklist below is for when the cause isn't already visible.

## Step 1: Get the actual evidence

Don't propose a fix from a paraphrased symptom. What's needed:

- The **full stack trace**, not the first line. The useful frame is
  usually three or four down, in user code.
- The **relevant source** — the component, the hook, how it's rendered.
  Ask if it hasn't been shared. Reconstructing the code from imagination
  and debugging the reconstruction wastes everyone's time.
- **When it happens**: first load, after navigation, dev only, production
  build only, after hot reload, on refresh, some users only.
- What **changed** just before it started.

If the report is "it doesn't work", the first job is turning that into a
reproducible observation — what was expected, what appeared.

## Step 2: Match against known signatures

Most React bugs are one of a small set. Check these before theorising.

**"Hydration failed" / "Text content did not match"**
Server HTML differs from the first client render. Usual causes:
`Date.now()`, `toLocaleString()`, `Math.random()`, `localStorage`/`window`
read during render, `typeof window !== 'undefined'` branching in JSX,
invalid HTML nesting (`<div>` inside `<p>`), timezone and locale
formatting, browser extensions injecting nodes. Fix by moving the
client-only value into an effect or `useSyncExternalStore` rather than
disabling SSR for the page.

**Infinite loop / "Maximum update depth exceeded"**
`setState` during render, an effect setting state it also depends on, or
a dependency that's a fresh object/array/function each render. Context
values are a frequent offender.

**Effect runs twice in development**
StrictMode double-invoking to surface missing cleanup — working as
intended. The bug is the missing cleanup or the non-idempotent effect.
Removing StrictMode hides it rather than fixing it.

**State one render behind / stale value in a callback**
Stale closure. A listener, timer, or effect captured an old render's
variables. Functional updater `setX(prev => …)`, a corrected dependency
array, or a ref for values that shouldn't trigger renders.

**Data flickers, or an old response overwrites a newer one**
Unaborted fetch race. Needs `AbortController` or an `ignore` flag in
cleanup, or a data library that handles it.

**List items keep the wrong state after sort, filter, or delete**
Array index used as `key`. Use a stable id.

**"window is not defined" / "document is not defined"**
Browser API touched during SSR. Move it into an effect, or
`next/dynamic` with `ssr: false` for that component specifically.

**"Cannot update a component while rendering a different component"**
A parent's setter called inside a child's render body. Move to an effect
or a handler.

**Works in dev, breaks in the production build**
Minification breaking reliance on `Function.name` or class names,
tree-shaken side-effect imports, env vars not exposed to the client
bundle, `process.env` read at runtime on the client.

**Input flips from uncontrolled to controlled**
`value={undefined}` on the first render. Default to `''`.

## Step 3: Narrow before fixing

When no signature matches, bisect instead of speculating:

- Comment out half the subtree. Does it persist?
- Replace the suspect data with a literal. Still broken?
- Network tab — is the request firing, and what came back?
- React DevTools — is the component re-rendering, and with what props?
- One targeted log at the boundary you're testing, plus a statement of
  what result confirms or kills the hypothesis.

The smallest reproduction that still fails usually *is* the answer.

## Step 4: Report

1. **Cause** — one or two sentences naming the mechanism and the
   responsible line or pattern.
2. **Fix** — the minimal change. Show the changed region unless the file
   is small.
3. **Why it happened** — one line, only if it's non-obvious or likely to recur.

When uncertain, name the hypothesis, say what evidence would confirm it,
and ask for that specific thing. "I need to see X" beats a confident
wrong answer.

## Working rules specific to debugging

- **One ranked hypothesis at a time.** Five possible causes handed over
  for the user to sort through is a way of not answering.
- **Clearing `node_modules`, `.next`, or restarting the dev server is a
  last resort, not an opener.** Suggest it when the evidence points at a
  stale artefact.
- **Don't silence the symptom** — no swallowing try/catch, no `?.` chain
  added to make an error disappear, no `eslint-disable` on a hooks
  warning without explaining why the warning is wrong.
- Skip "Ah, I see the issue!" and start with the cause.
