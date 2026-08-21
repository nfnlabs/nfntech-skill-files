---
name: testing
description: Flutter test suites — unit tests for mappers and pure logic, fixture factories, hand-written fakes, provider and bloc tests, widget tests, goldens, and the analyze, lint and CI gates around them. Read when adding tests, raising coverage, or fixing a flaky test.
---

# Testing

> A test earns its place by failing when the behaviour breaks. Fixtures are factories, doubles are fakes, and nothing touches a real network, clock or file system.

The fakes live beside their real implementations → `data-layer.md`. Diagnosing a failure that is not a test problem → `diagnostics.md`.

## 1 · Read the existing suite first

| Check | Where | What it settles |
|---|---|---|
| Doubles style | grep `class Fake`, `mockito`, `mocktail` | hand-written fakes or generated mocks |
| Shared helpers | `test/support/`, `test/helpers/` | reuse instead of re-inventing |
| Container setup | the nearest existing state test | how this repo builds and disposes |
| Extras | `bloc_test`, `fake_async`, `golden_toolkit`, `integration_test` in dev deps | what's available |
| Fixtures | `test/fixtures/` | captured payloads to parse against |

Copy the nearest existing test's shape. That matters more than any convention here, because
it carries the repo's implicit decisions.

`test/` mirrors `lib/` one-to-one:
`lib/features/orders/application/order_list.dart` → `test/features/orders/application/order_list_test.dart`.
Mirroring means you can always find the test for a file — and see at a glance that there
isn't one.

## 2 · Where to spend effort

| Layer | Tool | Cost | Write when |
|---|---|---|---|
| Pure logic — mappers, validators, formatters | plain `test()` | negligible | always; this is the highest signal per line |
| State holders | `ProviderContainer` / `bloc_test` | low | always, for async, error paths, pagination |
| Widgets | `testWidgets` | moderate | critical flows, complex conditional rendering, regressions |
| End to end | `integration_test` | high, brittle | one or two smoke flows, CI only |

Mocking three things to test one means you're at the wrong layer.

For anything crossing the network, five cases are the floor: success with data, success with
**empty** data, connection failure, 401, and a malformed payload. Then where relevant:
pagination end-of-list, double-tap on submit, and dispose mid-request.

## 3 · Fixture factories

```dart
Order _order({
  String id = 'o1',
  OrderStatus status = OrderStatus.pending,
  int itemCount = 3,
  String customerName = 'Test Customer',
}) => Order(id: id, status: status, itemCount: itemCount, customerName: customerName);

test('cancelled orders are not shippable', () {
  expect(_order(status: OrderStatus.cancelled).isShippable, isFalse);
});
```

Adding a required field to the model then touches **one line** instead of forty call sites —
which is the single biggest reason test suites get abandoned halfway through a project. The
one overridden parameter *is* the scenario, so the test reads as its own intent. Keep the
defaults boring and valid so an unrelated field can never be what makes a test pass; override
explicitly when a case needs something invalid.

Parse tests run against a **real captured response** in `test/fixtures/`, which is what
catches the API changing under you rather than confirming your own assumptions.

## 4 · Fakes over mocks

Prefer a hand-written fake for gateways, repositories and services: it is a real
implementation with in-memory state, so it exercises your interface honestly and doesn't
break when you add a method with a default. Give it a settable `failWith` so the error path
is one line, and a call log for the tests that care about interaction.

Reach for `mockito`/`mocktail` when you need interaction assertions, or to stub something
awkward to fake — a platform channel, a third-party SDK.

```dart
ProviderContainer makeContainer({List<Override> overrides = const []}) {
  final container = ProviderContainer(overrides: [
    appDependenciesProvider.overrideWithValue(AppDependencies.fake()),
    ...overrides,
  ]);
  addTearDown(container.dispose);          // beats a tearDown block; scoped to this test
  return container;
}

test('surfaces a display-ready message when the gateway fails', () async {
  final gateway = FakeOrderGateway()..failWith = const ServerException(message: 'boom');
  final container = makeContainer(
    overrides: [orderGatewayProvider.overrideWithValue(gateway)],
  );

  await container.read(orderListProvider.notifier).refresh();

  final actual = container.read(orderListProvider);
  expect(actual, isA<AsyncError>());
  expect(AppErrorHandler.resolve(actual.error!), isNot(contains('Exception')));
});
```

```dart
blocTest<SettingsBloc, SettingsState>(
  'debounced search hits the repository once',
  build: () => SettingsBloc(fakeRepository),
  act: (bloc) => bloc..add(Search('a'))..add(Search('ab')),
  wait: const Duration(milliseconds: 400),
  verify: (_) => expect(fakeRepository.calls, hasLength(1)),
);
```

Inject a clock rather than calling `DateTime.now()`; `fake_async` for debounce and polling;
seed any `Random`. `SharedPreferences.setMockInitialValues({})` in setup, and fake the secure
storage and permission channels, or the test dies on a `MissingPluginException`.

What to assert either way: a terminal state on success **and** failure; the loading flag set
**and** cleared; the error message display-ready; derived getters at their boundaries; and
that disposing mid-flight doesn't throw.

## 5 · Widget tests

```dart
extension PumpApp on WidgetTester {
  Future<void> pumpScreen(Widget child, {List<Override> overrides = const []}) =>
      pumpWidget(ProviderScope(
        overrides: [
          appDependenciesProvider.overrideWithValue(AppDependencies.fake()),
          ...overrides,
        ],
        child: MaterialApp(theme: AppTheme.light, home: child),
      ));
}

testWidgets('retry re-requests after a failure', (tester) async {
  final gateway = FakeOrderGateway()..failWith = const ServerException(message: 'x');
  await tester.pumpScreen(const OrderListScreen(),
      overrides: [orderGatewayProvider.overrideWithValue(gateway)]);
  await tester.pump();

  expect(find.byType(AppErrorView), findsOneWidget);

  gateway.failWith = null;
  await tester.tap(find.text(ErrorCopy.retry));
  await tester.pump();
  await tester.pump();                       // one pump per async hop
  expect(find.byType(AppListTile), findsWidgets);
});
```

Per screen worth testing: one test per state — loading, error, empty, content — plus one
interaction. That set catches nearly all real regressions and stays cheap to maintain.

Goldens are for design-system components, not screens with live data. Pin the surface size
and text scale, load fonts, run them on one platform in CI, and actually look at the diff —
a golden accepted unseen is worthless.

## 6 · Flake sources

| Symptom | Root cause | Correct fix |
|---|---|---|
| "pumpAndSettle timed out" | a spinner or looping animation never settles | `pump()` per async hop, or `pump(duration)` |
| Passes alone, fails in the suite | shared mutable global or a locator left registered | `getIt.reset()` / `addTearDown` |
| MissingPluginException | real platform channel in a test | mock prefs, secure storage, permissions in setup |
| Overflow errors nobody notices | default 800×600 surface | set `tester.view.physicalSize`; assert `takeException()` is null |
| Tap finds nothing | target off-screen | `scrollUntilVisible` first |
| Golden diffs on every machine | fonts not loaded, or renderer differs | load fonts; pin to one CI platform |
| Expected bloc states never arrive | `void` handler that awaits | fix the bloc, don't add a delay |
| Timing-dependent pass | `Future.delayed` used as synchronisation | `fake_async` or pump |
| Breaks when a model gains a field | models constructed inline | fixture factory with defaults |

A flaky test is worse than no test, because it trains people to re-run rather than read.
Reproduce with `flutter test --repeat 20 <file>`, fix the cause, and quarantine only with a
linked issue and a date.

## 7 · Gates

```sh
dart format --output=none --set-exit-if-changed .
dart run build_runner build --delete-conflicting-outputs
git diff --exit-code            # codegen drift is a failure, and the check people forget
flutter analyze                 # or: melos run analyze   (--fatal-infos)
dart run custom_lint            # riverpod_lint lives here, not in flutter analyze
flutter test --coverage
```

`--fatal-infos` matters because infos are where `riverpod_lint` and dead-code hints live, and
those catch the lifecycle bugs tests often miss. Strip generated files from coverage or the
number is meaningless — treat it as a map of untested areas rather than a target. A mapper at
0% is a real gap; a screen at 40% often isn't.

A boundary-check script — presentation importing data, Flutter inside domain, raw colours in
features — is cheap and belongs beside these. Keep its patterns precise; a check with false
positives gets disabled and then deleted.

## 8 · Done when

- New behaviour has a test that fails without the change
- Five network cases covered where the feature crosses the network
- Models built through factories, not inline
- Every double is a fake or a justified mock; nothing hits a real service
- Suite passes from clean, and twice in a row
- `flutter analyze`, `custom_lint` and the boundary script all clean
- Codegen committed in sync — `git diff --exit-code` passes
