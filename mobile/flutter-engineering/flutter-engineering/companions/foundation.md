---
name: foundation
description: Flutter project bootstrap and the decisions that shape a codebase — stack defaults with their retrofit costs, build order, bootstrap sequencing, analysis_options and lints, commit conventions, assets and fonts, and the Talker plus Crashlytics observability stack. Read when starting a project or wiring logging, crash reporting or CI.
---

# Foundation

> Build in an order where each step makes the next one cheap. Constants and theme exist before the first screen, because everything after copies the first screen.

Layout and routes → `architecture.md`. Flavors and builds → `environments.md`. State and DI shapes → `state.md`. Components → `design-system.md`. Gates → `testing.md`. Pre-release console pass → `release-readiness.md`.

## 1 · Read the repo

| Check | Where | What it settles |
|---|---|---|
| Stack | `pubspec.yaml` | state library, client, codegen, SDK constraint |
| Shape | `melos.yaml`, `flavorizr.yaml`, `lib/main*.dart` | single package or workspace, flavor mechanism |
| Binding rules | `CLAUDE.md`, `AGENTS.md`, `.cursorrules` | conventions that outrank this skill |
| Existing pattern | `lib/` two levels deep | whether anything is actually undecided |

An established pattern wins. Report it in one line and proceed. Don't refactor working code
toward this skill uninvited.

## 2 · Decide what's genuinely open

Batch these into one exchange with a proposed default each, rather than asking as you go. The
right-hand column is why the order in §3 is what it is — the expensive ones come first.

| Axis | Default | Retrofit cost |
|---|---|---|
| Package shape | single package unless several shippable sub-apps exist | high |
| State | Riverpod with codegen | high |
| DI | provider-graph object; `get_it` for app-lifetime infrastructure | medium |
| HTTP | `dio` | medium |
| Routing | `go_router` | high |
| Models | `freezed` + `json_serializable` | medium |
| Environments | `dev` / `qa` / `uat` / `prod` | high |
| **Auth model** | **ask — no safe default** | very high |
| **Localisation** | **ask — no safe default** | very high |

The last two are asked every time. Proceed on the rest unless told otherwise.

**Always ask, never assume:** the auth model (bearer + refresh, session cookie, API key,
none) and localization (English-only copy classes vs ARB). Both are expensive to retrofit,
and a wrong guess is discovered months later.

**Not questions at all:** the architecture and the flavor mechanism are prescribed — see
`flutter-architecture`. Ask *which environments*, not *which strategy*.

## 3 · Build order

```sh
flutter create --org com.example --platforms=ios,android my_app   # only platforms you ship
cd my_app && fvm use 3.35.0                                       # commit .fvmrc

mkdir -p lib/{app,config,core,shared/{theme,design,constants,widgets,models},features} \
         lib/platform_bridge test/{support,fixtures} assets/{fonts,shared}
```

1. Create and pin the SDK.
2. Dependencies, `analysis_options.yaml` (§5), folder skeleton per `flutter-architecture` §2.
3. `lib/app/` — bootstrap, the DI graph with its fake seam, the router.
4. `lib/config/` — `BuildType`, `BuildConfig`, per-flavor Firebase options, one `main.dart`.
5. **`lib/shared/` constants, theme, copy class — before the first screen.** The step people skip
   and the debt nobody repays.
6. `lib/core/` — logger, crash facade, global handlers (§6), one error resolver.
7. First feature end to end. It becomes the template everything else copies, so build it
   slowly and name it.
8. `test/support/` helpers and one real test.
9. CI gates per `flutter-testing` §7.

```dart
// lib/app/app_bootstrap.dart — order is the point of this file
Future<void> bootstrap() async {
  final config = BuildConfig();

  await runZonedGuarded(() async {
    WidgetsFlutterBinding.ensureInitialized();

    await Firebase.initializeApp(options: config.firebaseOptions);
    AppLogger.init(enableLogs: config.enableLogs);
    await Observability.init(flavor: config.type,
        collectCrashes: config.type != BuildType.dev);

    FlutterError.onError = (details) {
      AppLogger.instance.handle(details.exception, details.stack, 'FlutterError');
      FirebaseCrashlytics.instance.recordFlutterFatalError(details);   // FATAL, not Error
    };
    PlatformDispatcher.instance.onError = (error, stack) {
      AppLogger.instance.handle(error, stack, 'PlatformDispatcher');
      Observability.recordError(error, stack, fatal: true);
      return true;
    };

    await initDependencies(config);
    runApp(ProviderScope(
      observers: [TalkerRiverpodObserver(talker: AppLogger.instance)],
      child: const App(),
    ));
  }, (error, stack) {
    AppLogger.instance.handle(error, stack, 'Uncaught');
    Observability.recordError(error, stack, fatal: true);
  });
}
```

Everything is awaited before anything reads config, and the handlers are installed before the
first widget builds — otherwise the errors you most want to see are the ones you miss.

## 4 · Project wiring, end to end

Where each piece of configuration lives, and the single path through `main.dart` that ties
them together. This is the map people reconstruct from scratch on every new project.

### 4.1 What lives where

| Artefact | Location | Consumed by |
|---|---|---|
| Environment enum | `lib/config/build_type.dart` | `BuildConfig`, and anything gating on environment |
| Per-environment values | `lib/config/build_config.dart` | the network config, Firebase init, logging flag |
| Generated Firebase options, one per flavor | `lib/config/firebase_options_<flavor>.dart` | `Firebase.initializeApp` at runtime |
| Firebase native configs, source of truth | `config/firebase/android/google-services-<flavor>.json`, `config/firebase/ios/GoogleService-Info-<flavor>.plist` | referenced by `flavorizr.yaml` |
| Firebase native configs, platform-consumed | `android/app/src/<flavor>/google-services.json`, `ios/Runner/<flavor>/GoogleService-Info.plist` | the Gradle plugin and the Xcode build |
| Flavor definitions | `flavorizr.yaml` at the repo root | regeneration of the native side |
| DI registration | `lib/app/di.dart` — one function, called once | bootstrap |
| Provider accessors | `lib/app/app_providers.dart` | features |
| Bootstrap | `lib/app/app_bootstrap.dart` | `lib/main.dart` |
| Signing | `android/signing.properties`, `android/*.jks` — both gitignored | Gradle release build |

The Firebase configs appearing **twice** is the part that catches people. There are three
artefacts per flavor and they must agree: the checked-in source file, the copy flavorizr
places where each platform SDK expects it, and the generated Dart options used by
`Firebase.initializeApp`. Adding a SHA fingerprint in the console means re-downloading the
source file *and* re-running flavorizr, or the platform keeps using the stale copy — see
`release-readiness.md`.

Keep the per-flavor names suffixed (`-dev`, `-qa`) in the source location and unsuffixed at
the platform destination. Identical filenames in one directory is how the wrong project's
config gets committed over the right one.

In a Melos workspace this whole group belongs in one `core/environment` package rather than
the app shell, so feature packages depend on the config without depending on the app.

### 4.2 The path through `main.dart`

`main.dart` stays a single line so the ordering lives in one reviewable place:

```dart
// lib/main.dart
Future<void> main() => bootstrap();
```

```dart
// lib/app/app_bootstrap.dart
Future<void> bootstrap() async {
  final config = BuildConfig();                    // reads --dart-define; throws on unknown

  await runZonedGuarded(() async {
    WidgetsFlutterBinding.ensureInitialized();     // 1 · bindings before any plugin

    AppLogger.init(enableLogs: config.enableLogs); // 2 · logger first, so step 3 can report
    await Firebase.initializeApp(                  // 3 · the right project for this flavor
      options: config.firebaseOptions,
    );
    await Observability.init(                      // 4 · needs Firebase; off on dev
      flavor: config.type,
      collectCrashes: config.type != BuildType.dev,
    );

    FlutterError.onError = (details) {             // 5 · handlers before the first widget
      AppLogger.instance.handle(details.exception, details.stack, 'FlutterError');
      FirebaseCrashlytics.instance.recordFlutterFatalError(details);
    };
    PlatformDispatcher.instance.onError = (error, stack) {
      AppLogger.instance.handle(error, stack, 'PlatformDispatcher');
      Observability.recordError(error, stack, fatal: true);
      return true;
    };

    await initDependencies(config);                // 6 · everything below needs config
    runApp(const App());                           // 7 · first frame
  }, (error, stack) {                               // anything escaping the zone
    AppLogger.instance.handle(error, stack, 'Uncaught');
    Observability.recordError(error, stack, fatal: true);
  });
}
```

Each step exists where it does for a reason worth knowing:

- **Bindings first**, or any plugin call throws.
- **Logger before Firebase**, so a Firebase init failure is reported rather than swallowed.
- **Handlers before `runApp`**, because errors raised before they're installed are invisible —
  and startup is exactly where the interesting ones happen.
- **DI after config**, because the client's base URL comes from it.
- **`runZonedGuarded` wrapping everything**, as the last line of defence for anything the two
  handlers don't catch.

An `await` inserted between steps 6 and 7 — a remote-config fetch, a session restore, a
preload — is the usual cause of a slow cold start. Only config, logging and crash handling
genuinely need to precede the first frame; move the rest behind it and let the UI show a
loading state.

### 4.3 Registration order inside `initDependencies`

Registration order is dependency order. A façade registered before its dependency throws at
startup, which is at least loud and immediate.

```dart
Future<void> initDependencies(BuildConfig config) async {
  // 1 · leaves — no dependencies of their own
  final prefs = await SharedPreferences.getInstance();
  _once<AppLocal>(() => AppLocal(prefs, const FlutterSecureStorage()));

  // 2 · transport — base URL comes from config, never a literal
  _once<NetworkClient>(() => NetworkClient(config: NetworkConfig.fromBuildConfig(config)));

  // 3 · repositories and façades, which depend on 1 and 2
  _once<AuthRepository>(() => AuthRepository(getIt<NetworkClient>(), getIt<AppLocal>()));
  _once<AppSession>(() => AppSession(getIt<AppLocal>()));

  // 4 · anything needing a registered dependency to finish wiring
  getIt<NetworkClient>().attachAuthInterceptor(getIt<AuthRepository>());
}

void _once<T extends Object>(T Function() create) {
  if (!getIt.isRegistered<T>()) getIt.registerSingleton<T>(create());
}
```

The `isRegistered` guard is what makes hot restart and tests survive a second call. Step 4
exists because an auth interceptor needs the repository that the client itself feeds — resolve
that by attaching afterwards rather than by making two singletons hold each other.

Shapes for the objects being registered, and the Riverpod-side accessors, are in `state.md`.

## 5 · Record decisions in code

This skill set *is* the architecture reference, so there's no separate document to drift out
of sync. A choice that isn't obvious from the code gets a one-line comment at the site that
owns it. A decision that is an **absence** needs the comment most, because absence reads as
oversight:

```dart
/// English-only, intentionally. No flutter_localizations, no .arb files.
/// To add locales: add the dep, set `generate: true`, convert each block below to
/// app_en.arb, swap AppCopy.x for context.l10n.x, run `flutter gen-l10n`.
abstract final class AppCopy { /* … */ }
```

## 6 · Lints and commits

```yaml
# analysis_options.yaml
include: package:flutter_lints/flutter.yaml      # without this the file REPLACES the defaults

analyzer:
  plugins: [custom_lint]                         # the line that makes riverpod_lint run
  language: { strict-casts: true, strict-raw-types: true }
  errors:
    use_key_in_widget_constructors: error         # escalated so CI blocks, not just warns
    always_use_package_imports: error
    sort_constructors_first: error
    always_put_required_named_parameters_first: error
    invalid_annotation_target: ignore             # freezed noise
  exclude: ["**/*.g.dart", "**/*.freezed.dart", "build/**"]

linter:
  rules: [use_key_in_widget_constructors, always_use_package_imports,
          prefer_const_constructors, always_put_required_named_parameters_first,
          slash_for_doc_comments, sort_constructors_first]
```

The escalation is the technique worth copying: a rule listed only under `linter:` is a warning
people scroll past, while naming it again under `analyzer: errors:` makes `flutter analyze`
exit non-zero. Reserve it for mechanical, unarguable rules — escalating taste teaches people
to ignore analyzer output entirely. In a Melos repo every package needs its own options file,
or `melos run analyze` gives the modules analyzer defaults instead of your config.

Commits: `type(scope): imperative description`, lowercase, no trailing period, scope is the
feature in kebab-case — `fix(orders): show the cached total when the call times out`. One
logical change per commit, and codegen output ships with the source that generated it.

## 7 · Observability

The rule: **log locally always, report remotely only when unexpected.**

```dart
abstract final class Observability {
  /// Expected failures are logged, never reported — reporting them buries real crashes
  /// under noise, and then nobody reads the dashboard at all.
  static bool shouldReport(Object error) => switch (error) {
        ValidationException()   => false,
        UnauthorizedException() => false,   // session expiry is a flow, not a defect
        ForbiddenException()    => false,
        NotFoundException()     => false,
        ConnectionException()   => false,   // the user's wifi is not your crash
        TimeoutException()      => false,
        _                       => true,
      };
}

class CrashlyticsTalkerObserver extends TalkerObserver {
  @override
  void onError(TalkerError data) => _maybeReport(data.error, data.stackTrace, data.message);
  @override
  void onException(TalkerException d) => _maybeReport(d.exception, d.stackTrace, d.message);

  void _maybeReport(Object? e, StackTrace? s, String? reason) {
    if (e == null || !Observability.shouldReport(e)) return;
    Observability.recordError(e, s, reason: reason);
  }
}
```

The observer is what guarantees you cannot log an error and forget to report it — so feature
code only needs `AppLogger.instance.handle(e, s, '<where>')` and the wiring decides the rest.
Call `recordError` directly only when attaching extra custom keys, as the HTTP interceptor
does.

Crash collection off on dev, or your own hot-reload exceptions make the dashboard useless.
Route and state observers give breadcrumbs — "crashed on payment, arrived from checkout" is a
diagnosis where a bare stack trace isn't. No PII in keys, breadcrumbs or the user identifier:
opaque ids only, endpoint paths rather than full URLs, and `printRequestHeaders: false` on the
Dio logger. Force one test crash per release channel; an untested crash pipeline is usually a
broken one.

## 8 · Setup mistakes

| Symptom | Root cause | Correct fix |
|---|---|---|
| Modules linted differently from the app | no per-package `analysis_options.yaml` | one-line include per package |
| `riverpod_lint` never fires | `custom_lint` plugin not enabled | add it, and run `dart run custom_lint` |
| Only six lint rules active | missing `include:` line | include `flutter_lints` |
| Crash dashboard full of noise | everything reported | `shouldReport` predicate |
| Framework errors show as notes | `recordFlutterError` used | `recordFlutterFatalError` |
| Config read before it's ready | work before the config resolves | awaited bootstrap chain |
| Fonts look slightly wrong | weights not declared | declare every weight used |
| "Temporary" hardcoded colours everywhere | first screen built before constants | build step 5 before step 7 |

## 9 · Done when

- The open axes were asked, and the settled ones weren't
- Bootstrap awaits config, then logger, then crash handlers, then dependencies
- Constants, theme and copy class exist before any screen
- One logger, one crash facade, `shouldReport` in place, crash collection off on dev
- `flutter analyze` and `dart run custom_lint` clean
- CI runs format → codegen → `git diff --exit-code` → analyze → lint → test
- Non-obvious decisions carry a comment at the site that owns them
