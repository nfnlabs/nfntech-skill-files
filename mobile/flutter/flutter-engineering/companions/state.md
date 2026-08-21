---
name: state
description: Flutter state holders and the dependency injection feeding them — notifiers, blocs, cubits, providers, app-wide singletons, and the lifecycle rules preventing disposal and rebuild bugs. Read when adding or changing anything that holds state.
---

# State

> One idiom per codebase, and every await is followed by a liveness check before state is touched.

HTTP, gateways and typed errors → `data-layer.md`. Where holders live → `architecture.md`. Rendering → `design-system.md`.

## 1 · Signals to read first

| Check | Where | What it settles |
|---|---|---|
| State idiom | grep `@riverpod`, `extends StateNotifier`, `extends Bloc<` | which of the three you write |
| Codegen present | `*.g.dart` beside providers, `riverpod_generator` in dev deps | annotation vs hand-written |
| DI mechanism | grep `GetIt`, `getIt`, an `AppDependencies`-style class | where to register |
| Transport | `dio` / `http` / `retrofit` in `pubspec.yaml` | interceptors available or not |
| Error taxonomy | `*exception*.dart`, `*error_handler*.dart` | extend, don't invent a second one |

**The idiom of the file you are editing wins.** Never migrate a file's idiom as a side effect
of a feature change, and never run two in one feature — consistency is worth more than any
one idiom's advantages.

Route from what you found to the section you write against:

| What the sweep shows | Write | Section |
|---|---|---|
| `@riverpod` annotations with `*.g.dart` beside them | Riverpod codegen | §3 |
| `flutter_riverpod` and `StateNotifierProvider`, no generator | Riverpod + StateNotifier | §4 |
| `extends Bloc<Event, State>` or `extends Cubit<State>` | Bloc / Cubit | §5 |
| Nothing yet — greenfield | Riverpod codegen | §3 |

In a monorepo or a large app the answer can differ **per module**. Check the module you're
editing, not the root. A feature package on Bloc inside an app whose shell uses Riverpod is a
normal state of affairs, and the module's idiom is the one that binds you.

Riverpod codegen is the default for greenfield, because generated providers are mechanically
identical and `riverpod_lint` then catches the lifecycle mistakes for you. That reasoning does
not transfer to an existing Bloc codebase — there, Bloc is correct.

## 2 · Choosing the holder

| What it holds | Lifetime | Shape |
|---|---|---|
| Server data for one screen | dies with the screen | async holder; `build` returns the future, mutations via `AsyncValue.guard` |
| UI selection — tab, expansion, draft | dies with the screen | plain notifier or cubit, autoDispose, seeded in `build` |
| Long-lived service — poll, socket, session, native bridge | app lifetime | keepAlive or locator singleton, invoked never watched |
| Derived value — filtered list, total | free | a getter or selector, never a second stored field |

A keepAlive holder carries a one-line comment saying why it must outlive the screen.
Without it, the next reader assumes it was an accident and either copies the mistake or
"fixes" a deliberate choice.

## 3 · Riverpod codegen shapes

```dart
part 'order_list.g.dart';

@riverpod
class OrderList extends _$OrderList {
  @override
  Future<List<Order>> build() => ref.read(orderGatewayProvider).fetchOrders();

  Future<void> markShipped(String id) async {
    final gateway = ref.read(orderGatewayProvider);     // capture BEFORE awaiting
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      await gateway.markShipped(id);
      return gateway.fetchOrders();
    });
  }
}

/// keepAlive: owns the socket subscription; a screen change must not tear it down.
@Riverpod(keepAlive: true)
class DeviceSync extends _$DeviceSync {
  @override
  void build() => ref.onDispose(_subscription.cancel);
}
```

Two helpers worth carrying between projects, because both bugs are invisible until they hurt:

```dart
// 1 · Equal state still notifies. On a timer/socket/poll feed that means every consumer
//     rebuilds for nothing. Needs value equality on the elements — an argument for freezed.
void replaceAll(List<Device> next) {
  if (listEquals(state, next)) return;
  state = next;
}

// 2 · Updating one item in list-shaped state. Returns `this` on a miss, so a miss is a
//     no-op rather than a silent append, and the result is always a NEW list so the
//     assignment actually registers as a change.
extension PatchById<T> on List<T> {
  List<T> patch(String id, String Function(T) idOf, T Function(T) update) {
    final i = indexWhere((e) => idOf(e) == id);
    return i == -1 ? this : [...take(i), update(this[i]), ...skip(i + 1)];
  }
}
```

## 4 · Riverpod with StateNotifier

Four files per feature — page, notifier, freezed state, generated. `autoDispose` by default,
and `if (!mounted) return;` after every await.

```dart
final orderListProvider =
    StateNotifierProvider.autoDispose<OrderListNotifier, OrderListState>(
  (ref) => OrderListNotifier(ref.watch(orderGatewayProvider)),
);

class OrderListNotifier extends StateNotifier<OrderListState> {
  OrderListNotifier(this._gateway) : super(OrderListState()) {
    unawaited(_load());                       // kick off; don't await in a constructor
  }
  final OrderGateway _gateway;

  Future<void> _load() async {
    state = state.copyWith(isLoading: true, error: '');
    try {
      final orders = await _gateway.fetchOrders();
      if (!mounted) return;                   // the screen may already be gone
      state = state.copyWith(orders: orders, isLoading: false);
    } on NetworkException catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, error: AppErrorHandler.resolve(e));
    }
  }

  Future<void> refresh() => _load();
}
```

Keep the field names identical across features — `isLoading`, `error` as
empty-string-for-none, and the pagination trio — so a reader moving between features isn't
re-learning the contract. Reset `error` when a load starts and clear `isLoading` on **both**
paths; a notifier that only clears it on success strands a spinner forever.

## 5 · Bloc and Cubit

Reach for a **Bloc** when there are discrete, nameable intents worth an event class and an
audit trail; a **Cubit** when there aren't — a toggle, a form field, a filter. Both obey the
same lifecycle rules.

```dart
sealed class OrderListEvent {}
final class OrderListStarted extends OrderListEvent {}
final class OrderListRefreshed extends OrderListEvent {}
final class OrderShipped extends OrderListEvent {
  OrderShipped(this.id);
  final String id;
}

@freezed
abstract class OrderListState with _$OrderListState {
  const factory OrderListState({
    @Default(<Order>[]) List<Order> orders,
    @Default(false) bool isLoading,
    @Default('') String error,
  }) = _OrderListState;
}

class OrderListBloc extends Bloc<OrderListEvent, OrderListState> {
  OrderListBloc(this._gateway) : super(const OrderListState()) {
    on<OrderListStarted>(_onStarted);
    on<OrderListRefreshed>(_onStarted);                 // same handler, different intent
    on<OrderShipped>(_onShipped, transformer: droppable());  // ignore taps while in flight
  }

  final OrderGateway _gateway;

  // Future<void>, never void — a `void` handler that awaits then emits throws
  Future<void> _onStarted(OrderListEvent event, Emitter<OrderListState> emit) async {
    emit(state.copyWith(isLoading: true, error: ''));
    try {
      final orders = await _gateway.fetchOrders();
      if (isClosed) return;
      emit(state.copyWith(orders: orders, isLoading: false));
    } on NetworkException catch (e, s) {
      AppLogger.instance.handle(e, s, 'OrderListBloc._onStarted');
      if (isClosed) return;
      emit(state.copyWith(isLoading: false, error: AppErrorHandler.resolve(e)));
    }
  }
}
```

**Event transformers** are the Bloc-specific tool worth knowing, because the alternative is a
hand-rolled flag. `droppable()` ignores events arriving while one is in flight — the
double-tap guard. `restartable()` cancels the previous one, which is what search-as-you-type
wants. `sequential()` queues them, for writes that must not interleave. `concurrent()` is the
default and is rarely what you want for anything touching the network.

```dart
on<SearchChanged>(
  _onSearch,
  transformer: (events, mapper) =>
      events.debounce(const Duration(milliseconds: 350)).switchMap(mapper),
);
```

**State shape.** Either a freezed state class with flags, or a sealed hierarchy
(`OrderListLoading`, `OrderListReady`, `OrderListFailure`) the widget switches over
exhaustively. Both work; pick whichever the codebase already uses. A shared generic state
family reused across every bloc saves typing and costs you exhaustiveness — if widgets are
casting `dynamic` payloads out of it, that feature has earned its own sealed states.

**Never put `BuildContext`, `Navigator` or a dialog in a bloc.** Emit an intent and let a
`BlocListener` act on it. That is what keeps a bloc testable without a widget tree, which is
the main reason to use one.

On the widget side, split side effects from rendering and stop info-only states from
rebuilding:

```dart
BlocConsumer<OrderListBloc, OrderListState>(
  listenWhen: (prev, next) => next.error.isNotEmpty,
  listener: (context, state) => AppToast.show(context, state.error),
  buildWhen: (prev, next) => prev.orders != next.orders || prev.isLoading != next.isLoading,
  builder: (context, state) => …,
);
```

`BlocSelector` when one field drives the rebuild. Provide the bloc at the scope that owns it —
`BlocProvider` above the screen, disposed with it. A bloc provided app-wide is a service, and
needs the same justifying comment a keepAlive holder does.

**Testing** is `bloc_test`: `build` the bloc with a fake gateway, `act` to add events,
`expect` the state sequence, `wait` for debounced transformers, `verify` interactions. If
expected states never arrive, the cause is almost always a `void` handler — see
`testing.md`.

## 6 · Dependency injection

One registration site; nothing constructs its own repository.

```dart
class AppDependencies {
  AppDependencies({required this.orderGateway, required this.authGateway});
  AppDependencies.fake()
      : orderGateway = FakeOrderGateway(),
        authGateway   = FakeAuthGateway();
  final OrderGateway orderGateway;
  final AuthGateway authGateway;
}

@riverpod
OrderGateway orderGateway(Ref ref) => ref.watch(appDependenciesProvider).orderGateway;
```

Adding a dependency is one field plus one accessor, and the whole graph fakes in a single
override — which is precisely what makes widget tests cheap enough that people write them.

```dart
Future<void> initDependencies(BuildConfig config) async {
  final prefs = await SharedPreferences.getInstance();

  if (!getIt.isRegistered<AppLocal>()) {                 // guard: hot restart + tests
    getIt.registerSingleton<AppLocal>(AppLocal(prefs, const FlutterSecureStorage()));
  }
  if (!getIt.isRegistered<AppRemote>()) {
    getIt.registerSingleton<AppRemote>(
      AppRemote(NetworkClient(config: NetworkConfig.fromBuildConfig(config))),
    );
  }
  if (!getIt.isRegistered<AppRepository>()) {            // façades last
    getIt.registerSingleton<AppRepository>(
      AppRepository(getIt<AppRemote>(), getIt<AppLocal>()),
    );
  }
}
```

Registration order is dependency order — a façade registered before its dependency throws at
startup, which is at least loud. Mixing is normal: `get_it` owns app-lifetime infrastructure,
Riverpod owns per-screen state, providers may read from `get_it`, and a `get_it` singleton
must never read from a Riverpod container.

**Shared singletons** — `AppRemote`, `AppLocal`, `AppRepository`, `AppSession` — are ordinary
constructor-injected classes. No `static` mutable fields, no top-level mutables, no
self-instantiating `factory X() => _i ??= X()`. A class that reaches for a global cannot be
faked or reset between tests, which is the whole reason the rule exists. Read them at the edge
— a provider body, a bloc's construction site — never inside a business method and never from
`build`.

Session end is not object disposal: clearing constants leaves the singleton registered, and
re-registering on logout leaves widgets holding the old instance. Clear session, storage and
caches in one place on logout, and dispose anything owning a socket or stream.

## 7 · Failure modes

| Symptom | Root cause | Correct fix |
|---|---|---|
| "Tried to use X after dispose" | state or `ref` touched after an `await` | `ref.mounted` guard, or capture deps into locals first |
| "emit was called after the handler completed" | `void` Bloc handler that awaits | make it `Future<void>`; `isClosed` before late emits |
| "Cannot emit new states after calling close" | emit after the bloc's scope was disposed | `isClosed` check; provide the bloc at the right scope |
| Double submit charges twice | concurrent handler with no guard | `droppable()` transformer, or disable while in flight |
| Search fires a request per keystroke | no debounce or `restartable()` | debounce + `switchMap` in the transformer |
| Spinner never clears | loading set, cleared only on success | clear on both paths; `AsyncValue.guard` does it for you |
| UI ignores an update | collection mutated in place, same reference passed to `copyWith` | build a new collection |
| Rebuilds several times a second | equal state reassigned on a poll | equality guard before assignment |
| Whole screen rebuilds on one field | watching the state object, not the field | `select` / `BlocSelector` / `buildWhen` |
| Widget casts `dynamic` out of state | one generic state family shared by every bloc | sealed states for that feature |
| Navigation happens twice | bloc navigating, plus a listener doing it too | emit an intent; only the listener acts |
| Logout leaves the previous user's data | singleton cleared in one place, cached in another | clear session, storage and caches together |
| Test can't replace a dependency | class constructs its own, or reads a global | constructor injection + a registered Fake |

Transport and gateway failures are in `data-layer.md` §4.

## 8 · Done when

- One idiom in the touched module; no hand-written provider in a codegen repo
- Every `await` followed by a liveness check before state is touched
- Loading cleared and error reset on both success and failure paths
- Error in state is display-ready — `isNot(contains('Exception'))` passes
- Long-lived holders and app-wide singletons carry a justifying comment
- Dependencies registered once, real **and** fake
- Bloc handlers are `Future<void>`; anything user-triggerable twice has a transformer or a guard
- `flutter analyze` and `dart run custom_lint` clean
