---
name: design-system
description: Flutter presentation conventions — design constants, ThemeData, the shared component set, screen and widget file rules, user-facing copy, assets and fonts, accessibility and responsive layout. Read when writing or changing any widget, screen, sheet, dialog, form or list.
---

# Design System

> Every visual value comes from a constant, every string from the copy layer, and every screen branches loading → error → empty → content in that order.

Where state comes from → `state.md`. File placement and routes → `architecture.md`. Jank in existing screens → `diagnostics.md`.

## 1 · Locate the vocabulary

| Looking for | Typical home | If absent |
|---|---|---|
| Colours | `shared/theme/app_colors.dart`, a `*_res.dart`, a theme extension | create in the repo's style |
| Spacing · radius · shadows | `shared/design/` | create the scale, don't inline numbers |
| Text styles | `app_text_styles.dart` or `textTheme` | define one ramp |
| Components | `shared/widgets/`, a `ui_components` package | build §3's set first |
| Copy | `shared/constants/app_copy.dart`, or `.arb` files | copy classes, note it's English-only |
| Assets | `assets.gen.dart` or an `AppAssets` class | constants, never raw paths |

Answer all six before typing a widget. Guessing here is how a screen ends up with its own
private design system.

## 2 · Constants

```dart
abstract final class AppColors {
  // named by ROLE, not hue — `primarySurface`, never `lightBlue2`
  static const Color primary        = Color(0xFF0B5FFF);
  static const Color primarySurface = Color(0xFFE8F0FF);
  static const Color textPrimary    = Color(0xFF1A1A1A);
  static const Color textSecondary  = Color(0xFF6B6B6B);
  static const Color error          = Color(0xFFD92D20);
  /// Design constant `Alert/Amber` — warning chips on light surfaces, fill at 12%.
  static const Color warning        = Color(0xFFB54708);
}

abstract final class AppSpacing {
  /// 4 — hairline padding inside chips and badges.
  static const double xxs = 4;
  /// 8 — tight gaps within a compact group.
  static const double xs = 8;
  /// 12 — default gap between text rows in a card.
  static const double sm = 12;
  /// 16 — card padding, comfortable widget spacing.
  static const double md = 16;
  /// 24 — screen-edge padding for headings.
  static const double xl = 24;
}

abstract final class AppRadius {
  static const double md = 12;
  static const BorderRadius rMd = BorderRadius.all(Radius.circular(md));
  static const BorderRadius rPill = BorderRadius.all(Radius.circular(999));
}
```

The doc comment on each spacing step says what it is *for*, so the next person picks by
intent instead of eyeballing. Exposing both the value and a ready-made `BorderRadius` keeps
call sites short and diffs small.

Escalation order for any visual value: existing constant → constant × a documented multiplier →
a **new** constant named by intent, with a comment citing the design source → never a literal.

**Domain constant enums** for values that must look identical everywhere:

```dart
enum SeverityTier {
  ok(label: 'OK', ceiling: 50, color: AppColors.success),
  watch(label: 'Watch', ceiling: 200, color: AppColors.warning),
  critical(label: 'Critical', ceiling: 999, color: AppColors.error);

  const SeverityTier({required this.label, required this.ceiling, required this.color});
  final String label; final int ceiling; final Color color;

  static SeverityTier fromValue(int v) =>
      values.firstWhere((t) => v <= t.ceiling, orElse: () => critical);
}
```

Now the summary dot, the chart marker and the detail card cannot disagree — which they will,
eventually, if each computes its own colour.

**Typography, centralised once.** Six to eight named styles, the font family written in
exactly one place, fed into `textTheme`. Twenty styles means nobody knows which to pick and
people quietly return to `TextStyle(fontSize: 15)`. Choose one access route — theme lookup or
the constants class — for the whole codebase; maintaining both is how the two drift.

**Theme carries the repeated decisions:**

```dart
ThemeData get lightTheme => ThemeData.light().copyWith(
  textTheme: AppTextStyles.theme.apply(bodyColor: AppColors.textPrimary),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    border: OutlineInputBorder(borderRadius: AppRadius.rMd, borderSide: BorderSide.none),
    focusedBorder: OutlineInputBorder(borderRadius: AppRadius.rMd,
        borderSide: const BorderSide(color: AppColors.primary)),
    contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md, vertical: AppSpacing.sm),
  ),
  appBarTheme: const AppBarTheme(elevation: 0, centerTitle: false),
);
```

Styling the third `ElevatedButton` by hand means the theme is wrong — fix it there instead.
If the app ships light-only, pin `themeMode` and say so, rather than leaving system dark to
render a palette nobody has tested.

## 3 · The component set to build before the first screen

```
shared/widgets/            or  ui_components/lib/src/widgets/
  buttons/     app_button.dart
  fields/      app_text_field.dart · app_dropdown_field.dart
  feedback/    app_loading.dart · app_error_view.dart · app_empty_state.dart · app_toast.dart
  layout/      app_app_bar.dart · app_list_tile.dart · gap.dart
  media/       cached_image.dart
  modals/      confirmation_modal.dart
```

```dart
class AppButton extends StatelessWidget {
  const AppButton({
    super.key,
    required this.label,                    // a String, so the component owns typography
    required this.onPressed,                // null == disabled; don't add an `enabled` flag too
    this.variant = AppButtonVariant.primary,   // enum, not four booleans
    this.isLoading = false,
    this.expanded = false,
  });
  ...
}
```

Three rules matter more than the styling, because each is a bug the component exists to
prevent: **loading implies disabled**, or a double tap submits twice; the button **must not
resize** when it enters loading, so keep the label in the tree at zero opacity behind the
spinner rather than swapping it out; and the spinner colour comes from the variant's
foreground, not a hardcoded white.

- **`AppLoading`** — one spinner, one size scale (16 inline, 24 default, 40 page). A bare
  `CircularProgressIndicator` in feature code inherits whatever the ambient theme says.
- **`AppEmptyState`** — distinguish *nothing exists yet* (offer create) from *your filter
  matched nothing* (offer clear filters). Collapsing both into "No data" is the most common
  list-screen defect.
- **`AppErrorView`** — takes an already-resolved message plus a retry callback. It never sees
  an exception and never calls `toString()`. Offer retry whenever the action is retryable; a
  dead-end error screen makes people force-quit.
- **`AppTextField`** — visible label, not placeholder-only (that fails accessibility and
  disappears once typing starts); `errorText` reserving its line so the layout doesn't jump
  when validation fires; keyboard type and input action set on every field.
- **`AppListTile`** — owns its own divider, so a list is `ListView.builder` with no separator
  logic; ellipsized title; ≥48 dp target even when dense.
- **`AppAppBar`** — `String` title, plus a back hook so a form screen can intercept for
  unsaved changes without reimplementing the leading button.

Promote into the shared library only when two or more features need it, it holds no
feature-specific logic, and its API is required params plus optional overrides. A library of
one-use widgets is worse than the duplication it replaced.

## 4 · Screen skeleton

```dart
@override
Widget build(BuildContext context, WidgetRef ref) {
  final state = ref.watch(orderListProvider);

  return Scaffold(
    appBar: AppAppBar(title: OrderCopy.listTitle),
    body: state.when(
      loading: () => const AppLoading(size: 40),
      error: (e, _) => AppErrorView(
        message: AppErrorHandler.resolve(e),                  // resolved, never raw
        onRetry: () => ref.read(orderListProvider.notifier).refresh(),
      ),
      data: (orders) => orders.isEmpty
          ? AppEmptyState(
              title: OrderCopy.emptyTitle,
              actionLabel: OrderCopy.create,
              onAction: () => context.pushNamed(RouteNames.orderCreate),
            )
          : RefreshIndicator(
              onRefresh: ref.read(orderListProvider.notifier).refresh,
              child: ListView.builder(
                itemCount: orders.length,
                itemBuilder: (_, i) => AppListTile(
                  title: orders[i].reference,
                  showChevron: true,
                  onTap: () => context.pushNamed(RouteNames.orderDetail,
                      pathParameters: {RouteParams.id: orders[i].id}),
                ),
              ),
            ),
    ),
  );
}
```

Same four branches in the same order on every screen, so a reader can skim any screen in the
app. One public widget per file. A screen past ~400 lines splits into `widgets/`; a `build`
past ~80 lines extracts into widget **classes**, not helper methods returning `Widget` —
helpers cannot be `const` and rebuild with the parent.

Widgets read state, render, dispatch intent. No network calls, no prefs, no timers, no
business rules, no repository imports.

## 5 · Copy, assets, fonts

Copy classes: one block per feature, interpolation as a function rather than concatenation at
the call site. ARB: add the key to every locale in the same commit, ICU plurals rather than a
Dart ternary, never concatenate translated fragments, and expect a 2–3× longer translation to
fit. Either way error text comes from the copy layer keyed off a normalized error type, and
accessibility labels are copy too.

```yaml
flutter:
  assets:
    - assets/orders/          # per-feature folders, registered as folders
    - assets/shared/
  fonts:
    - family: AppSans
      fonts:
        - { asset: assets/fonts/AppSans-Regular.ttf,  weight: 400 }
        - { asset: assets/fonts/AppSans-Medium.ttf,   weight: 500 }
        - { asset: assets/fonts/AppSans-SemiBold.ttf, weight: 600 }
        - { asset: assets/fonts/AppSans-Bold.ttf,     weight: 700 }
```

Declare every weight you use, or Flutter synthesises the missing ones and the result looks
subtly wrong beside the design. A flat `assets/` folder is unnavigable by month three and
hides dead files.

## 6 · Defects to catch

| Symptom | Root cause | Correct fix |
|---|---|---|
| Design change misses one screen | hardcoded colour or padding there | constant, added if it doesn't exist |
| Text clipped at large font size | fixed-height box around wrapping text | let it size; test at 200% scale |
| "…" or overflow stripe in a row | unbounded `Text` beside other children | `Expanded` + `overflow: ellipsis` |
| Layout jumps when validation fires | `errorText` line not reserved | reserve it in the field component |
| Same button styled three ways | per-widget styling instead of theme | move it into `ThemeData` |
| Screen shows a raw exception | widget resolving errors itself | resolved message from the state layer |
| "No data" for both empty cases | one empty state for two meanings | separate copy and action per case |
| Icon button unusable with a screen reader | no `semanticLabel` | label it; treat it as copy |
| List stutters past a hundred rows | `Column` in a `SingleChildScrollView` | `ListView.builder` |
| Untested dark palette ships | `ThemeMode.system` with light-only constants | pin the mode, or build the dark set |

Grep your own diff before reporting; all should be empty outside constants files:

```sh
git diff -U0 | grep -nE "Color\(0x|EdgeInsets\.(all|symmetric|only)\([0-9]|circular\([0-9]|fontSize: [0-9]"
git diff -U0 | grep -nE "Text\('[A-Z]"
```

## 7 · Done when

- Zero raw colours, paddings, radii, font sizes or user-facing strings in the diff
- Reused existing components; anything new justified by two consumers
- Four branches present and in the standard order
- Tested with long content and at 200% text scale
- Icon-only controls labelled; targets ≥48 dp; contrast ≥4.5:1
- `ListView.builder` for anything that can exceed ~20 rows
- New assets registered, new font weights declared
