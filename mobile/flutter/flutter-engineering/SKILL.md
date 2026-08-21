---
name: flutter-engineering
description: Owns Flutter and Dart engineering — the entry point that reads what a project already is, then routes to the companion file owning the area being touched. Triggers on any Flutter work — starting an app, joining an existing codebase, adding a feature, screen, provider, bloc, repository or endpoint, styling, routing, flavors, builds, store releases, tests, and diagnosing crashes, jank or technical debt.
---

# Flutter engineering

> Read the codebase before advising it, then open exactly one companion. An existing
> convention outranks anything written in these files.

## 1 · Route by task

| The task | Open |
|---|---|
| New project bootstrap, lints, commits, logging, crash reporting | `companions/foundation.md` |
| Folder layout, layer boundaries, feature slices, routes and deep links | `companions/architecture.md` |
| Notifiers, blocs, providers, DI, shared singletons, lifecycle | `companions/state.md` |
| HTTP client, interceptors, auth refresh, gateways, DTOs, typed errors | `companions/data-layer.md` |
| Constants, theme, components, copy, assets, accessibility | `companions/design-system.md` |
| Unit, state, widget and golden tests; CI gates | `companions/testing.md` |
| Flavors, build config, signing, APK, AAB, IPA | `companions/environments.md` |
| Firebase and store console checks before shipping | `companions/release-readiness.md` |
| Crashes, jank, rebuild churn, leaks, refactor sequencing | `companions/diagnostics.md` |

One companion, occasionally two. Loading five for one change buries the answer under context
that doesn't apply.

## 2 · Read the project first

Never skip this on a codebase that already exists — every companion's advice is a comparison
against what's there, and you can't compare against an assumption.

```sh
cat pubspec.yaml                                   # stack and majors
ls melos.yaml flavorizr.yaml .fvmrc lib/main*.dart 2>/dev/null
ls CLAUDE.md AGENTS.md .cursorrules 2>/dev/null    # binding; outranks these files
find lib -maxdepth 3 -type d | sort
grep -rl "@riverpod\|extends StateNotifier\|extends Bloc<" lib modules 2>/dev/null | head
dart run build_runner build --delete-conflicting-outputs && git diff --stat   # codegen drift
```

Five answers decide how your change should look: **which state idiom** (and whether it's
consistent), **where DI happens**, **whether a typed error family exists**, **whether design
constants exist**, and **which existing feature is the cleanest example**. That last one is the
most valuable — a named reference implementation carries a hundred conventions no document
can describe.

Package majors matter. Freezed, Riverpod, `go_router` and Dio all changed shape across
majors, which makes a remembered pattern wrong rather than merely dated. Read the installed
version before writing against it.

## 3 · Greenfield or in flight

| Signal | Then |
|---|---|
| Empty repo, or `lib/` holding only `flutter create` scaffolding | **Greenfield** — you choose the stack; `companions/foundation.md` has the defaults and the build order |
| Features, screens or modules already shipped | **In flight** — the codebase has answered most questions; extend it consistently |
| Structure but no code worth keeping | ask before treating it as greenfield |

The distinction matters because the same advice flips sign. "Use Riverpod codegen" is a sound
greenfield default and, in a Bloc codebase, a proposal to introduce a second idiom — which is
worse than either idiom alone.

In flight means: adopt, then propose. Match local naming, file layout and error handling,
including idioms these files would not have chosen. Improvements are a separate short list
with costs attached, not applied inside an unrelated change. Don't reformat files you happened
to open, and don't "fix" an undocumented deliberate choice without asking — English-only copy,
a keepAlive provider and a hand-written parser all look like accidents and often aren't.

## 4 · Feature slice order

The one sequence worth stating here, because working inward from the screen produces models
shaped by widget convenience:

1. Name the reference feature you're copying — `architecture.md`
2. Domain models and pure logic — no Flutter, no IO
3. Data: interface, real impl, **Fake**, typed exception — `data-layer.md`
4. Register the dependency, real **and** fake — `state.md`
5. State holder — `state.md`
6. Screen and widgets — `design-system.md`
7. Route: name, path, registration — `architecture.md`
8. Tests: pure logic, then state against the Fake — `testing.md`

Step 3's Fake isn't a testing afterthought; it's what makes steps 5 and 8 cheap. Skipping it
is why features end up untested.

## 5 · Invariants

These hold in every companion, so they're stated once. A change breaking one is wrong even
when it compiles and the tests pass.

1. **Dependencies point one way** — presentation → application → data → domain. Domain imports
   no Flutter and does no IO.
2. **One idiom per codebase** for state, DI, errors and navigation. The file you're editing
   decides, not your preference.
3. **Liveness before state.** After any `await` the holder may be disposed — check before
   touching state. The most common Flutter runtime error.
4. **Typed errors at the boundary.** Transport exceptions become typed exceptions in the data
   layer; one resolver turns those into user-facing copy. No raw exception reaches a widget.
5. **No literals in feature code** — colours, spacing, font sizes and strings come from constants
   and the copy layer.
6. **Config is not code.** Base URLs and keys come from the flavor config; nothing in the
   binary is secret.
7. **Generated code ships with its source**, in the same change.
8. **The consoles are part of the release.** Signing fingerprints, push credentials and
   symbols are verified against the artifact that ships, not the local build.

## 6 · Working rules

Say which companion you followed and, on an existing codebase, which reference feature you
copied — it makes a wrong route cheap to correct. Where the codebase and a companion disagree,
the codebase wins and you say so. Ask only what the code can't answer: the authentication
model and whether the app will be localised have no safe default and are expensive to
retrofit. Everything else is visible in the repo or has a defensible default.

Finish with `flutter analyze`, `dart run custom_lint` and the tests, and name anything you
deliberately left undone.
