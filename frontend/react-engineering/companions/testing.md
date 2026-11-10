# Testing frontend code

Test behaviour a user could observe, at the cheapest layer that can
observe it. A test that breaks when you refactor without changing
behaviour is a liability, not coverage.

## Read the project's stack first

`grep -n "vitest\|jest\|playwright\|testing-library\|msw" package.json`.
Match what's there. For a new project: **Vitest** (Vite or Next with a
little config) or **Jest** (if the framework template already ships it) —
don't run both — plus **React Testing Library**, **MSW**, and
**Playwright**.

## Which layer

| Layer | Tool | Use for |
|---|---|---|
| Unit | Vitest / Jest | Pure logic: formatters, reducers, validators, schema parsing, query-key factories |
| Component | Testing Library + the runner | A component or hook with its real children, user events, and mocked network |
| End-to-end | Playwright | A handful of critical journeys across real routing, cookies, and server code: sign-in, checkout, the main create flow |
| Static | `tsc`, ESLint | Types and hook rules — already a test layer; run in CI |

Rough shape: many unit/component tests, few e2e. Don't e2e what a component
test covers, and don't component-test what is one pure function.

## Component tests with Testing Library

- Query the way a user finds things: `getByRole` (with `name`) first, then
  `getByLabelText`, `getByText`. `getByTestId` is the last resort and a
  hint the markup lacks an accessible name. Role queries double as an
  accessibility check.
- `userEvent` (`const user = userEvent.setup()`, then
  `await user.click(...)`), not `fireEvent`. Component tests need a DOM
  environment (`jsdom` or `happy-dom`) configured in the runner.
- Await async UI with `findBy*` / `waitFor`; never `setTimeout` or a bare
  sleep. Assert absence with `queryBy*`.
- Don't assert on implementation: component state, internal hook calls,
  the number of renders, snapshot of a large tree.
- Wrap with the app's real providers via one shared `renderWithProviders`
  in `src/test/`. A fresh `QueryClient` per test with `retry: false`, or
  cached data leaks between tests.
- Test hooks through a component that uses them, or `renderHook` when the
  hook is the public API.
- Server Components that `await` data aren't unit-testable in the runner
  today in most setups; test their pure parts, and cover the rendered
  result with Playwright *(version-dependent — check current guidance for
  the installed Next.js)*. Browser-side mocking can't intercept what a
  Server Component fetches on the server, so for e2e stub the upstream
  API with a stub server, MSW running in the server process, or a seeded
  test API.

## Mocking the network

Mock at the network boundary with **MSW**, not by mocking `fetch`, the
axios module, or the data hook. The code under test then runs its real
fetching, parsing and error paths.

- Handlers in `src/test/handlers/`, shared by component tests, and — if the
  team wants it — by Storybook and local dev.
- `onUnhandledRequest: 'error'`, so a new request fails the test instead of
  silently hitting the network.
- Override per test (`server.use(...)`) for the error and empty cases;
  reset in `afterEach`.
- Keep handlers honest: type them against the same schemas the app parses
  responses with.
- Mock only what you don't own and can't run: the network, time
  (`vi.useFakeTimers` in Vitest, `jest.useFakeTimers` in Jest), randomness, browser APIs missing in jsdom
  (`IntersectionObserver`, `matchMedia`). Don't mock your own modules to
  make a test pass.

## What to cover, per feature

For every component or feature that fetches, the four states each have a
test: **loading, empty, error, success**. Plus: the main interaction, a
validation failure on any form, and the permission or edge case that has
bitten you before. Skip trivial presentational components with no logic.

## Playwright

- A short list of critical journeys, not a copy of every component test.
- Locate with roles and labels, same as Testing Library. Rely on
  auto-waiting; no `waitForTimeout`.
- Authenticate once via `storageState` in a setup project, not through the
  UI in every test.
- Tests are independent and runnable in any order, with their own data;
  don't depend on a previous test's leftovers.
- Run against a production build in CI. Keep traces and screenshots on
  failure; quarantine a flaky test with a ticket rather than retrying
  forever.
- Add `@axe-core/playwright` on key pages for automated accessibility
  checks — a floor, not a substitute for keyboard testing. At component
  level, `jest-axe` (its matcher also works registered in Vitest) or `axe-core`
  directly with Testing Library covers the same ground — `vitest-axe` is
  barely maintained, so verify it before choosing it; automated tools catch only a minority of WCAG issues, so tab
  through new UI by hand too.

## What each PR must include

- Tests for new behaviour and for the bug fixed — a bug fix without a
  regression test that fails before the fix is incomplete.
- All four states tested for anything that fetches.
- No `.only`, no skipped test without a linked ticket, no snapshot updated
  without reading the diff.
- Typecheck, lint, and the test suite green locally and in CI; coverage
  not lower on touched files. Coverage is a smoke alarm, not a target —
  see `nfn-core:engineering-baseline` for the team's CI gates.
- If the change is visual, a screenshot or Storybook link in the PR.

## Working rules specific to testing

- Don't write tests that mirror the implementation line by line.
- Don't add `data-testid` everywhere to make queries easy; fix the
  accessible name instead.
- A failing test is information: fix the code or the test deliberately,
  never loosen an assertion until it passes.
- State which layer you chose for each test and why, in a line.
