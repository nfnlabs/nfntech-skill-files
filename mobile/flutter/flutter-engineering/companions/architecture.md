---
name: architecture
description: Flutter code placement and navigation — layer structure, the canonical feature slice, boundary enforcement, and go_router routes, deep links and redirects. Read when adding a feature, screen or module, moving files under lib/, adding a route, or reviewing a diff for layering violations.
---

# Architecture

> A feature is a vertical slice with four layers, dependencies point one way, and every route carries both a name and a path.

State holders → `state.md`. Data access → `data-layer.md`. Widgets → `design-system.md`. Flavors and builds → `environments.md`.

## 1 · Signals to read before deciding

| Check | Where | What it settles |
|---|---|---|
| Layout shape | `find lib -maxdepth 2 -type d` | feature-first vs legacy flat vs monorepo |
| Package graph | `pubspec.yaml`, `melos.yaml` | single package or Melos workspace |
| Flavor mechanism | `flavorizr.yaml`, `lib/main*.dart`, `String.fromEnvironment` | how environments are selected |
| Binding conventions | `CLAUDE.md`, `AGENTS.md`, `.cursorrules` | rules that outrank this skill |
| Codegen state | `*.g.dart`, `*.freezed.dart` freshness | whether build_runner must run first |

An existing layout wins. Match it, say so in one line, and don't convert working code as a
side effect — that's a separate agreed task.

## 2 · The canonical slice

```
lib/
  app/                    app_bootstrap.dart · di.dart · router.dart · route_names.dart
                          route_paths.dart
  config/                 build_type.dart · build_config.dart · firebase_options_<flavor>.dart
  core/                   cross-cutting SERVICES — logging, crash, connectivity, analytics
  shared/                 cross-cutting VALUES & WIDGETS — theme, design, constants, widgets
  platform_bridge/        pigeon schemas + generated native clients
  features/<feature>/
    domain/
      models/             freezed models, enums, route-arg objects
      <feature>_mapper.dart      pure functions — the cheapest thing to unit test
    data/
      <feature>_gateway.dart     abstract interface
      rest_<feature>_gateway.dart
      fake_<feature>_gateway.dart   first-class, lives in lib/ not test/
      <feature>_exception.dart
      request/ response/         DTOs, once the wire shape diverges from domain
    application/          notifiers / blocs — the only layer that orchestrates
    presentation/
      <feature>_screen.dart
      widgets/
  main.dart               ONE entrypoint; flavor arrives as a build argument
```

Layer permissions, which is the part that actually gets violated:

| Layer | May import | Must never import |
|---|---|---|
| `domain` | pure Dart only | Flutter, Riverpod/Bloc, dio, anything doing IO |
| `data` | `domain` | widgets, state holders |
| `application` | `domain`, `data` | widgets |
| `presentation` | `domain`, `application` | `data`, `platform_bridge` |

`core` holds side effects; `shared` holds values and dumb widgets. Keeping them separate is
what stops `core` slowly becoming a second `lib`.

**Melos variant.** Same four layers inside each package. One `MaterialApp`, in the root
shell — sub-apps are plain widgets. Every package exports a barrel, so nothing deep-imports
`src/`. `apps/*` → `core/*` only, never the reverse and never app-to-app. A new module lands
in three files: its own pubspec, the consumer's pubspec, `melos.yaml`.

## 3 · Placement resolution

Ask in order, stop at the first yes:

1. Performs IO — network, channel, disk, prefs? → **data**
2. Coordinates across more than one call, or holds state? → **application**
3. Plain data or a pure function, no Flutter, no IO? → **domain**
4. Widget-shaped, used by exactly one feature? → **presentation/widgets/**
5. Two or more features need it? → **promote** — service to `core/`, value or widget to `shared/`

Rule 5 is the one that gets skipped. A widget pasted into a second feature should have been
promoted; a `shared/` widget with one consumer should come back down.

## 4 · Scaffolding a feature

Copy the cleanest existing slice and name which one — that beats any template, because it
inherits the conventions this document can't fully describe.

```dart
// domain/models/order.dart — Freezed 3.x: `abstract`, plus a private ctor for custom members
part 'order.freezed.dart';
part 'order.g.dart';

@freezed
abstract class Order with _$Order {
  const Order._();
  const factory Order({
    required String id,
    required OrderStatus status,          // enum, never a String, never two bools
    @Default(<String>[]) List<String> tags,
  }) = _Order;

  factory Order.fromJson(Map<String, dynamic> json) => _$OrderFromJson(json);

  bool get isCancellable => status == OrderStatus.pending;
}
```

Freezed 2.x wants a plain `class` and will not compile with `abstract`, so read the installed
major first. An enum status makes `switch` exhaustive, so the analyzer tells you what you
forgot when a case is added — that is the entire reason to prefer it over a string.

Then in order: gateway + Fake + typed exception → DI registration → state holder → screen →
route → copy and constants → tests.

## 5 · Boundary violations to catch

| Symptom in the diff | Why it matters | Correct move |
|---|---|---|
| `presentation` imports `data/` or `platform_bridge/` | couples UI to transport; kills widget tests | go through the application layer |
| `package:flutter/` inside `domain/` | domain stops being testable without a binding | move the Flutter-dependent part up a layer |
| Feature A reads feature B's gateway | two owners for one resource | consume B's application layer |
| Business rule inside a widget `State` | untestable, re-runs on rebuild | move to the state holder |
| `package:x/src/…` across packages | bypasses the barrel; two copies of one class | export it from the barrel |
| A `path:` dep missing from `melos.yaml` | codegen and analyze silently skip it | add it in the same commit |
| Per-flavor `main_<flavor>.dart` files | duplicates bootstrap; drifts | one entrypoint, flavor as an argument |
| `kDebugMode` used as an environment check | a QA *release* build is a real thing | read `BuildConfig` |

Both of these belong in CI, because a boundary nothing enforces is a preference:

```sh
grep -rnE "import .*(/data/|/repositories/|platform_bridge/)" \
  --include="*_screen.dart" --include="*_page.dart" lib modules
grep -rln "package:flutter/" lib/features/*/domain
```

## 6 · The three files

Three files, and nothing else declares a route: `route_paths.dart` (templates, param keys),
`route_names.dart` (name constants), `router.dart` (routes, redirect, errorBuilder).

```dart
GoRoute(
  name: RouteNames.orderDetail,          // both, always
  path: RoutePaths.orderDetail,          // ':id' — relative, no leading slash on a child
  builder: (context, state) => OrderDetailScreen(
    id: state.pathParameters[RouteParams.id]!,
  ),
  routes: [ /* children keep the back stack correct and deep links restorable */ ],
);

context.pushNamed(
  RouteNames.orderDetail,
  pathParameters: {RouteParams.id: order.id},
);
```

Navigate by **name**; paths exist for URLs and deep links. Interpolating
`'/orders/${order.id}'` at call sites turns every path change into a find-and-replace the
compiler cannot help with. A leading slash on a child path silently promotes it to top-level
and the nesting quietly does nothing.

Path parameters carry identifiers only. For an object, refetch by id in the destination — it
survives a cold deep link — or pass a freezed args class through `extra`, never a `Map`.
`extra` is not serialisable, so an extra-only route cannot be deep-linked; give it an
id-based fallback.

`StatefulShellRoute` for persistent tab chrome; plain `ShellRoute` loses each branch's state,
which is why tabs "forget" their scroll position. All auth gating lives in the one `redirect`,
reading already-resolved state so it stays synchronous, returning `null` when nothing is
needed, and never able to return the route it was called from.

## 7 · Failure modes

| Symptom | Root cause | Correct fix |
|---|---|---|
| Nested route behaves as top-level | child path has a leading slash | make child paths relative |
| Back button leaves the flow entirely | pushed a sibling instead of declaring a child | declare it under `routes:` |
| Deep link opens a blank or default screen | route depends on `extra`, which is not serialisable | id-based path params with a refetch |
| Tabs lose scroll position | plain `ShellRoute` instead of `StatefulShellRoute` | switch to the stateful variant |
| Infinite redirect | a redirect branch can return the route it was called from | return `null` when no redirect is needed |
| Navigation feels sluggish app-wide | `redirect` awaits a repository on every navigation | read already-resolved state; keep it synchronous |
| A path change broke six call sites | navigation by path, not name | `pushNamed` with the name constant |
| Route argument is a `Map` | untyped, unchecked at every read | a freezed args class in `domain/` |

## 8 · Done when

- Slice has all four layers, and the two greps above print nothing
- Route registered by name; no literal path at a call site
- Freezed major matches the syntax used; codegen run and committed
- Every flavor builds on **both** platforms, not just the one you touched
- Two flavors install side by side, with different names and icons
- Startup log or debug screen confirms flavor, base URL and Firebase project
- `git diff | grep -iE "key|token|secret|password"` is clean
