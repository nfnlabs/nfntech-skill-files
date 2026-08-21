---
name: diagnostics
description: Diagnosis of existing Flutter code by reading it — crashes, exceptions, wrong behaviour, jank, rebuild churn, wasted work per frame, slow startup, leaks, and refactor sequencing. Read when something is broken, slow, or resists change.
---

# Diagnostics

> Name the mechanism and the line before proposing a change. The evidence is the source plus whatever the user already has.

The conventions this judges against live in `architecture.md`, `state.md`, `data-layer.md`, `design-system.md` and `testing.md`.

## 1 · Skip the procedure when the answer is visible

If the pasted evidence already contains it — a one-line error with the offending line, a
signature from §3 that matches unambiguously — say what's wrong and fix it. Running a
narrowing procedure as ceremony wastes the user's time and buries the answer.

The rest of this applies when the cause isn't already on screen.

## 2 · Route the request

| The user's words | Track | Read |
|---|---|---|
| crashes · throws · wrong data · a stack trace | **Defect** | §3 |
| slow · janky · stutters · rebuilds too much · memory climbs | **Waste** | §4 |
| clean up · refactor · too much duplication | **Debt** | §5 |

If the words fit two tracks, say which you picked in one line and continue. Two rules hold
across all three: never edit before you can point at the line, and report before you fix
unless they've already said "fix it" — people need the option to disagree with a diagnosis.

## 3 · Defect track

A stack trace answers most of it. The exception type names a class of mistake; the topmost
frame in your own code is where to start reading; and an `<asynchronous suspension>` marker
means an `await` sits between frames, which is where most lifecycle bugs live.

| Error | Mechanism | Correct fix |
|---|---|---|
| "Tried to use X after dispose" | state or `ref` touched after an `await` in an autoDispose provider | `ref.mounted` guard, or capture deps into locals before awaiting |
| "emit was called after the handler completed" | `void` Bloc handler that awaits | make it `Future<void>`; `isClosed` before late emits |
| "setState() called during build" | state mutated in `build`, or a listener firing synchronously during it | move the effect to a listener or post-frame callback |
| "Looking up a deactivated widget's ancestor" | `BuildContext` used after the widget is gone, usually post-`await` | capture first, then check `context.mounted` |
| `LateInitializationError` | `late` field read before assignment — an init-order bug | make it nullable or fix the order; `late` isn't a way to defer thinking |
| "null is not a subtype" on JSON | trusted a field the API didn't send | parse defensively at the DTO; surface a typed parse error |
| "setState after dispose" | async work outliving the widget | mount check after every await; cancel subscriptions in `dispose` |
| Works on one device only | almost always data-specific, not device-specific | find that account's payload; check nullable and numeric-type assumptions |

When nothing matches, narrow rather than speculate. **Trace the value across layer
boundaries** — is it already wrong in the gateway's response, or does it go wrong in the
mapper, the holder, the widget? That one question resolves most "wrong data on screen" bugs,
and it is the practical payoff of having layers at all. Then vary the input (empty, null,
unicode, expired constant) and re-read the code as though the widget vanishes mid-`await`.
`git log -S'<symbol>'` is worth it when the regression window is known.

A defect is closed when the mechanism is gone **and** a test would fail without the fix. Name
that test; for lifecycle bugs it's a holder test against a fake, not a widget test.

## 4 · Waste track

You are looking for work repeated per frame, per row or per rebuild that could happen once,
later, or never. All of it is visible in source, which is why this needs no device.

Be honest about the limit: reading code tells you *what* is expensive and *why*, not *how
much* on a given handset. Rank by mechanism, don't invent numbers, and if the user supplies
their own measurements use those to order the list.

| Pattern in the source | Cost | Fix |
|---|---|---|
| `sort`/`where` on a collection inside `build` | every rebuild; and sorting provider-owned data there mutates shared state, so it's also a correctness bug | sort in the holder, expose the ordered list |
| `DateFormat`, `RegExp`, `jsonDecode` constructed per row | once per row per rebuild | hoist to a static or the holder |
| Controller or timer created in `build` | leaks, plus re-created per rebuild | `initState`, disposed in `dispose` |
| Helper methods returning `Widget` | can't be `const`; rebuild with the parent | extract widget classes |
| Whole screen watching a state object | any field change rebuilds everything | `select` / `BlocSelector` / `buildWhen` |
| State reassigned with an equal value | notifies for nothing on every poll | equality guard before assignment |
| `Column` of N rows in a `SingleChildScrollView` | builds and lays out all N, visible or not; keeps them all mounted | `ListView.builder`, `itemExtent` when uniform |
| Blur, opacity, shader mask, anti-aliased clip or large soft shadow **per row** | extra compositing work per row per frame — the classic scroll stutter, and no Dart optimisation touches it | hoist the effect out of the repeating element, or pre-bake it |
| `Image.network` / `AssetImage` with no target size | decodes at full source resolution regardless of display box | `cacheWidth`/`cacheHeight` or `ResizeImage` |
| Platform view inside a list row | the most expensive thing you can put in a tree | one in the chrome at most |
| Network call or sequential awaits before `runApp` | delays first frame | only config, logging and crash handlers precede it; parallelise the rest |
| `initState` with no matching `dispose` | leak | mirror every subscription, controller and timer |
| keepAlive holder appending forever, cache with no eviction | unbounded growth | bound it, or scope it to the screen |

Note the two-way link between the last group and the eager-list row: many large decodes alive
at once is usually the eager list showing up as a memory symptom rather than a separate
problem. Say so, because fixing the list fixes both.

Rank the findings and give the reason for the order — "per row per frame" versus "once per
data change" is what makes a ranking trustworthy rather than a list. Then name the single
cheapest check that would confirm the top item on their device, so they measure once to
confirm instead of exploring blind.

## 5 · Debt track

If you can't name the change it makes easier, it isn't a refactor — it's rearranging, with
risk and no payoff. Say what it enables before starting.

Tests come first. A refactor without tests on the code being moved is a rewrite with extra
steps, so write characterisation tests to pin current behaviour. And never mix a refactor
with a behaviour change in one commit: when something breaks afterwards, nobody can tell which
half did it.

**Sequencing matters when duplication has diverged.** If three copies exist and one is missing
a fix the others got, that's a live bug rather than untidiness — fix the divergence *first*,
as its own commit, then extract. Extracting first forces you to preserve the bug through the
extraction, usually behind a flag parameter that shouldn't exist.

| Worth doing | Not worth doing |
|---|---|
| Duplication that has **diverged** | Renaming for taste |
| A god file split along seams that already exist | An abstraction with one implementation |
| A boundary violation that keeps causing bugs | Splitting a long but cohesive file nobody touches |
| `Map<String, dynamic>` where a model belongs — the analyzer starts helping immediately | Restyling code that already follows the project's conventions |
| A missing seam in code that constructs its own dependency | Anything about to be deleted |

Move one thing, run analyze and the tests, commit. If the analyzer goes red you've left
behaviour-preserving territory — stop and understand why before continuing.

## 6 · Reporting shape

1. **Cause or verdict in one sentence, first.** People read two lines and skim the rest, so a
   conclusion buried under methodology is a wasted report.
2. **Findings, ranked**, each with `file:line`, the mechanism, and a concrete fix. Keep it
   under ten — thirty means you're transcribing lint output, so group the repetitive ones and
   lead with what matters.
3. **Verified versus inferred.** "I couldn't confirm this from the source; based on the trace
   it's likely X" is far more useful than a confident wrong diagnosis.
4. **What you didn't cover**, when you skipped something. Silence reads as "everything else is
   fine", which is how a clean bill of health becomes worthless.

Severity: **critical** for crashes, data loss, security, or wrong data shown to a user;
**high** for a bug on a real path or a compounding boundary violation; **medium** for fragile
or untested; **nit** for preference.

Write for the user, not about the process — no references to skill sections, mode names or
internal terminology in the output they read.

## 7 · Anti-patterns in your own answer

| Tempting | Why it's wrong |
|---|---|
| Five possible causes for the user to sort through | that's a way of not answering; give one ranked cause |
| try/catch around a type error | hides the mechanism; it returns somewhere less obvious |
| A mount check where the real problem is IO in a widget | treats the symptom, leaves the design bug |
| "Optimised the list" with no mechanism named | unreviewable, and unverifiable later |
| Invented timings or "3× faster" | nobody measured it; it destroys trust in the real findings |
| Refactoring while debugging | two changes, one commit, no attribution |
| Filler findings to look thorough | devalues the ones that matter |
| A confident guess where the code is genuinely ambiguous | say what's missing and what would settle it |

If you found nothing significant, say so plainly and name what you checked. That is a real
result.

## 8 · Done when

- The mechanism is named and anchored to a line
- The fix addresses the cause, not the symptom
- For a defect: the test that fails without the fix is named or written
- For waste: findings ranked with the reason for the order, no invented numbers
- For debt: divergence fixed before extraction, tests first, one concern per commit
- Confidence stated; skipped areas listed
- `flutter analyze` and `flutter test` clean where the repo allows running them
