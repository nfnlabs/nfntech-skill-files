# Reviewing and refactoring frontend code

A review earns its place by changing what happens next. Praise, recaps,
and style nitpicks presented as findings all dilute that.

## Order of attention

Review in this order, and don't lead with formatting when the data flow
is broken.

1. **Correctness** — does it do what it claims, edge cases included?
2. **State and effects** — highest-yield category in React code.
3. **Boundaries** — server/client, module boundaries, what reaches the browser.
4. **Accessibility** — invisible in review, expensive later.
5. **Types** — does the type system constrain anything here?
6. **Performance** — only where it's structural, not micro.
7. **Naming and style** — last, and briefly.

## What to look for

**State and effects**
- State duplicating a prop, or duplicating state that could be derived.
- Effects doing work that belongs in a handler or during render.
- Missing cleanup on subscriptions, timers, listeners, observers.
- Dependency arrays that are wrong rather than merely noisy, and
  `eslint-disable` comments covering them.
- Fetch in an effect with no abort, no dedupe, no error path.
- Array index as `key` in a list that reorders or filters.
- Context value objects recreated every render.
- `value={undefined}` flipping an input from uncontrolled to controlled.

**Boundaries and data**
- A client directive at the top of a tree that mostly doesn't need it.
- Server-only config reachable from the client bundle.
- External data typed as though it were trusted. Casting `fetch().json()`
  to an interface is a lie the type system will repeat back to you.
- `dangerouslySetInnerHTML` without sanitisation.
- User-controlled values interpolated into `href` (`javascript:` URLs) or
  into query strings unencoded.

**Accessibility**
- `div`/`span` with `onClick`, no keyboard path, no role.
- Inputs without associated labels; placeholder standing in for a label.
- No accessible name on icon-only controls.
- Focus unmanaged on open and close of dialogs and menus.
- Colour as the only signal for state or error.

**Types**
- `any`, or a cast defeating the check next to it.
- Optional-everything props where a discriminated union would make
  invalid states unrepresentable.
- Types describing shape but not invariant — `string` for an id with a
  format.

**Structure**
- Missing loading, empty, or error states in something that fetches.
- A component doing fetching, transformation, and presentation at once
  *when that's causing a problem* — not merely because it's long.
- Duplication that has diverged, which is a bug in waiting. Duplication
  that hasn't diverged is often fine.

## Output format

Group findings by severity:

- **Blocking** — bug, security issue, data loss, broken accessibility.
- **Should fix** — will cause a problem soon, or makes the next change harder.
- **Nit** — genuine preference. Three maximum, marked optional.

Per finding: location, one sentence on why it matters, the concrete
replacement. Corrected code for blocking items; a sentence suffices for
nits.

If the code is fine, say so in a line and stop. That's a complete review.

## Refactoring rules

- Smallest change that removes the problem class. Don't rewrite the file.
- No silent behaviour changes. If behaviour must change, call it out separately.
- Keep the project's existing conventions even where they differ from
  your preference. Consistency beats taste.
- If the change needs a migration, describe the steps rather than
  dumping a rewritten file.

## Working rules specific to review

- Don't manufacture findings to look thorough. Three padding nits around
  one real bug buries the bug.
- Don't cite "best practices" as authority. Say what breaks, or leave it out.
- Separate "this is wrong" from "I'd do it differently", and mark the
  second optional.
