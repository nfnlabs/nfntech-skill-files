---
name: data-layer
description: The Flutter data layer — HTTP client configuration, interceptor ordering, single-flight token refresh, gateways with fakes, DTO and domain separation, the typed exception family, pagination and cancellation. Read when adding or changing an endpoint, repository, gateway or interceptor.
---

# Data Layer

> Domain objects and typed exceptions are the only things that leave this layer. No transport type, map or status code escapes it.

State consuming this → `state.md`. Where the base URL is defined → `environments.md`. Fakes in tests → `testing.md`.

## 1 · Client & interceptors

```dart
class NetworkClient {
  NetworkClient({required NetworkConfig config, Dio? dio})     // `dio` exists for tests
      : _dio = dio ?? Dio(BaseOptions(
          baseUrl: config.baseUrl,                             // from BuildConfig, never literal
          connectTimeout: config.connectTimeout,
          receiveTimeout: config.receiveTimeout,
        )) {
    _dio.interceptors.addAll([
      HeaderInterceptor(),           // locale, app version, device id
      AuthInterceptor(...),          // attach + single-flight refresh
      ErrorMappingInterceptor(),     // DioException -> typed, log, conditionally report
      if (config.enableLogging)      // LAST, and off in prod
        TalkerDioLogger(talker: AppLogger.instance,
          settings: const TalkerDioLoggerSettings(printRequestHeaders: false)),
    ]);
  }
  final Dio _dio;
  Dio get dio => _dio;
}
```

`printRequestHeaders: false` because the bearer token lives there. Adding the same
interceptor twice — easy when auth is wired later by DI — doubles refresh attempts, so
`removeWhere` before adding.

**Refresh is single-flight.** Five parallel 401s must trigger one refresh, so hold a
`Completer` and let the others await it. A `retried` marker on the request options prevents an
infinite loop when the new token is also rejected. Login and refresh endpoints carry a
skip-auth flag so they cannot recurse. Session expiry is a **callback** — the app shell
decides what logged-out looks like, not an interceptor. Never refresh or log out on **403**;
that means authenticated-but-not-permitted.

**Base URL chain:** flavor → `BuildConfig` → `NetworkConfig` → `BaseOptions.baseUrl`, set once
at construction. Gateways pass **paths only**, from a constants class. A second service means
a second named client, not one absolute URL at a call site. If changing environment requires
editing a feature file, the chain is broken.

## 2 · Gateways, DTOs, errors

```dart
abstract class OrderGateway {
  Future<List<Order>> fetchOrders({int page});
  Future<void> markShipped(String id);
}

class RestOrderGateway implements OrderGateway {
  RestOrderGateway(this._client);
  final NetworkClient _client;

  @override
  Future<List<Order>> fetchOrders({int page = 1}) async {
    try {
      final res = await _client.dio.get(ApiPaths.orders, queryParameters: {'page': page});
      return OrderListResponse.fromJson(res.data as Map<String, dynamic>)
          .data.map(Order.fromDto).toList();
    } on DioException catch (e) {
      throw mapDioError(e);                       // typed, always
    } on FormatException catch (e) {
      throw ParseException(message: 'Unexpected response shape', details: e);
    }
  }
}

class FakeOrderGateway implements OrderGateway {
  FakeOrderGateway({List<Order>? seed}) : _items = [...?seed];
  final List<Order> _items;
  Exception? failWith;                            // one line to test the error path
  final List<String> calls = [];
  ...
}
```

The Fake belongs in `lib/` beside the real one so widget tests, an offline mode and a demo
build can all use it. Register it in the fake graph in the same commit as the real one — a
half-wired fake graph is why people give up on widget tests.

Separate DTOs from domain models once the wire shape diverges. DTOs mirror the API including
its ugliness; the mapper that fixes the shape is a pure function and the single
highest-value unit test in this layer. Parse defensively — `json['x'] as String? ?? ''` —
because a field the API "always" sends will one day be absent.

Errors are three separate jobs. **Typed at the boundary:** a `NetworkException` family with
`ConnectionException`, `TimeoutException`, `UnauthorizedException`, `ValidationException`,
`ServerException`, `ParseException`. **One resolver** turning a typed exception into a
display-ready string from the copy layer — two competing mappers is how "Something went
wrong" and "An error occurred" end up on adjacent screens. **Reporting is separate again:**
log everything with its stack, report only the unexpected.

## 3 · Pagination & cancellation

Same field names in every feature — `items`, `currentPage`, `pageSize`, `hasMorePages`,
`isLoading`, `isLoadingMore` — with `canLoadMore` as a getter used as the guard clause at the
top of `loadMore`, which is what stops a fast scroll double-fetching. Append rather than
replace; refresh resets to page one; de-duplicate by id when rows shift between pages;
debounce search 300–400 ms.

One `CancelConstant` per screen, cancelled on dispose, so a stale response cannot overwrite
fresh state. Treat cancellation as not-an-error. Retry only idempotent requests on transient
failures, with backoff and a cap — never a bare POST, and never as a substitute for the
refresh flow.

## 4 · Failure modes

| Symptom | Root cause | Correct fix |
|---|---|---|
| Stack trace or `Exception: …` on screen | raw exception left in state | map to typed at the boundary, resolve to copy |
| Five refreshes on one token expiry | refresh not single-flight | shared `Completer`; others await it |
| Infinite refresh loop | new token also rejected, no retry marker | `retried` flag on the request options |
| Logged out on a permissions error | 403 treated as expiry | refresh on 401 only |
| Stale row overwrites a fresh one | no cancellation | `CancelConstant` per screen, cancelled on dispose |
| Cancelled request shown as an error | `cancel` not special-cased | treat cancellation as not-an-error |
| Bearer token in the logs | logging interceptor printing headers | `printRequestHeaders: false`; redact |
| Two refresh attempts per 401 | interceptor registered twice by DI | `removeWhere` before adding |
| Works on one account only | a field the API omits, cast unguarded | defensive parse at the DTO; typed parse error |
| Second service needs a different host | absolute URL at a call site | a second named client instance |
| Environment change needs a code edit | base URL not flowing from config | fix the config chain |
| Test can't replace the gateway | repository constructs its own client | constructor injection + a registered Fake |

State-holder and DI failures — disposal, spinners, rebuild churn — are in `state.md` §7.

## 5 · Done when

- No transport type, `Map`, or status code in a signature outside this layer
- Every gateway has an interface, a real implementation and a `Fake`
- Transport errors typed at the boundary; one resolver produces user copy
- Base URL and keys flow from the flavor config; paths come from a constants class
- Refresh is single-flight with a retry marker; 403 does not log out
- Failure paths covered in tests: 401, 5xx, timeout, malformed payload, empty list
