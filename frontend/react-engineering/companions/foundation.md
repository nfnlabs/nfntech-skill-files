# Foundation: structure, tooling, budgets

For a new project, or for deciding where something belongs. On an existing
codebase, everything here is a comparison target — the repo's current
layout and config win, and a gap is a note, not a silent fix.

## Folder structure

Organise by feature, with a thin shared layer. Group-by-type
(`components/`, `hooks/`, `utils/` holding everything) stops scaling around
the second team.

```text
src/
  app/ (or pages/, routes/)     # routing only: layouts, pages, route handlers — thin
  features/<name>/
    components/                 # UI used only by this feature
    api/                        # fetchers, query keys, DTO schemas for this feature
    hooks/  lib/  types.ts
    index.ts                    # types and client-safe exports only — see barrel rule below
  components/ui/                # design-system primitives, no business logic
  lib/                          # cross-feature: http client, env, formatting, auth helpers
  test/                         # test utilities, MSW handlers, fixtures
```

- A feature imports from `components/ui` and `lib`, never from another
  feature's internals. If two features need the same thing, it moves to
  `lib` or `components/ui`.
- **Barrel rule.** A feature's `index.ts` re-exports only types and
  client-safe modules. Never re-export server-only code (database access,
  secrets, server fetchers marked `server-only`) alongside client
  components — one barrel import then drags server code into the client
  graph and defeats tree-shaking (`perf.md`). Keep server fetchers in
  `api/server.ts` and client query hooks in `api/client.ts`, and import
  them by file path, not through the barrel. Prefer no barrel at all in
  large features.
- Pages and route files compose: they may `await` the feature's server
  fetchers and render feature components, but hold no business logic. A
  page longer than a screen has a feature component missing.
- Colocate: a component's test, story and styles sit next to it.
- Path alias (`@/`) for anything crossing a feature boundary; relative
  imports within one.

## TypeScript

- `"strict": true` is the floor. Beyond it, turn on
  `noUncheckedIndexedAccess` (array/record reads are `T | undefined`) and
  `exactOptionalPropertyTypes` where the team can absorb it; add
  `noImplicitOverride`, `noFallthroughCasesInSwitch`,
  `forceConsistentCasingInFileNames`, `isolatedModules`.
- `any` is banned by lint (`@typescript-eslint/no-explicit-any`); use
  `unknown` and narrow. `@ts-expect-error` with a reason beats
  `@ts-ignore`.
- Derive types from schemas (`z.infer<typeof schema>`) rather than writing
  the interface and the validator twice.
- On an existing loose codebase, don't flip `strict` in one commit — enable
  per-flag and fix by directory, or ask.

## Lint and format

- One formatter (Prettier or Biome), run on save and in CI; never debated
  in review.
- ESLint with the framework's config (`eslint-config-next` or the Vite/React
  equivalent), `eslint-plugin-react-hooks` (`rules-of-hooks` and
  `exhaustive-deps` as **errors**), `jsx-a11y`, and `typescript-eslint`
  type-aware rules. Add the React Compiler lint rules if the compiler is on.
- A `lint` and a `typecheck` script in `package.json`, both run in CI. Run
  `tsc --noEmit` as its own CI step so type errors fail independently of
  build config (`next build` type-checks by default, but
  `ignoreBuildErrors` can disable it). Don't hardcode a framework's lint
  command in docs — the project's script is the interface.
- Pre-commit (lint-staged) for formatting only; the full gates live in CI —
  see `nfn-core:engineering-baseline`.

## Toolchain compatibility

"Latest of everything" does not always install together: plugins' peer
ranges lag new majors. Before pinning a toolchain, read each package's
peer ranges (`npm view <pkg> peerDependencies`) and run a trial
`npm install`; fix conflicts by pinning the *tool* the plugins depend on,
not with `--force` or `--legacy-peer-deps`.

Conflicts seen in the npm registry on 2026-11-10 (re-check; these age).
npm may still install an out-of-range pair with only a warning, so
"it installed" is not proof it is supported:

| Pair | Finding |
|---|---|
| `typescript-eslint` 8.72 and TypeScript 7.0 | `typescript-eslint` declared `typescript >=4.8.4 <6.1.0`, so TypeScript 7 is outside its range. Stay on the newest TypeScript it supports until it widens. |
| `eslint-plugin-jsx-a11y` 6.10.2 and ESLint 10 | The plugin declared `eslint` up to `^9` and has had no release since 2024. Prefer the version bundled by `eslint-config-next`, or stay on ESLint 9 for projects that need it directly. |
| `vitest-axe` 0.1.0 | Single early release (January 2025), little maintenance. Prefer `jest-axe`'s matcher registered in Vitest, or call `axe-core` directly. |

`npm audit` on the same date: the runtime set (Next, React, zod, React Hook
Form, TanStack Query, DOMPurify, next-intl, Zustand, Redux Toolkit and
others) reported **0 vulnerabilities**. The dev toolchain reported **14**
(5 high, 9 moderate), all transitive and dev-only: the 5 high came from
`@lhci/cli` → `proxy-agent` → `basic-ftp` (CPU denial of service in an FTP
client, not reachable from a Lighthouse run), and the 9 moderate from
`minimatch` inside ESLint and `typescript-eslint`, fixable only by upstream
releases. Treat these as findings to record and re-check, not to wave away:
keep such tools out of production bundles, run them in CI only, prefer
newer releases when they land, and never `npm audit fix --force` blindly,
because it can downgrade a tool a major version.

Also: ESLint 9+ uses flat config (`eslint.config.*`); old `.eslintrc`
snippets are wrong there. Check Node.js minimums (Next.js 16 needs a
recent Node 20 LTS) and the TypeScript minimum in the framework's upgrade
guide. Use the framework's codemods for major upgrades
(`npx @next/codemod@latest`), then re-run typecheck, lint, tests and
`npm audit`.

## Environment config

- Validate env once at startup with a schema (zod) in one `lib/env.ts`;
  import from there, never `process.env` scattered through components.
- **Reference each public variable literally** when building the object to
  parse: `NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL`. Next.js
  inlines only literal `process.env.NEXT_PUBLIC_X` expressions, so
  `schema.parse(process.env)` in a module the browser imports leaves every
  public variable `undefined` in production, silently. (Vite exposes
  `import.meta.env` as an object, but still only `VITE_`-prefixed keys
  reach the browser.) A helper such as `@t3-oss/env-nextjs` does the
  mapping for you. Keep server-only variables in a separate module
  guarded with `server-only`.
- Split the schema into server and public parts. Public = `NEXT_PUBLIC_*` /
  `VITE_*`, inlined at build, visible to everyone — see `security.md`.
- Commit `.env.example` with every key and no values.

## Performance budgets

Set them at the start; a budget added after launch is a wish. Agree numbers
per project — these are defaults for a typical content/app page on a
mid-range mobile device over a throttled connection, measured at the 75th
percentile in the field where possible:

| Metric | Budget |
|---|---|
| LCP | ≤ 2.5 s |
| INP | ≤ 200 ms |
| CLS | ≤ 0.1 |
| Initial JS per route (gzipped, client) | ≤ 170 KB, stricter for marketing pages |
| Total page weight on first load | ≤ 1 MB without media |

Enforce in CI (Lighthouse CI, `size-limit`, or the bundler's budget
feature) so a regression fails a PR, not a quarterly review. Diagnosis
lives in `perf.md`.

## i18n

Decide on day one even if only one locale ships; retrofitting is a rewrite
of every string.

- Use a library (`next-intl`, `react-i18next`, FormatJS) — no hand-rolled
  lookup tables.
- No concatenated sentences; use ICU messages with placeholders and
  plurals. No string-built dates, numbers or currencies: `Intl.*` with the
  active locale.
- Locale in the URL (`/en/…`), not only in a cookie, so pages are cacheable
  and linkable. Set `<html lang>` and `dir`.
- Leave layout slack: translated strings run 30–40% longer.
- Hydration trap: formatting dates with the user's locale on the server and
  client differently — see `debug.md`.

## Analytics and personal data

- Route all tracking through one module (`lib/analytics.ts`) with a typed
  event catalogue; no `gtag(...)` calls scattered through components.
- Consent before load: no non-essential scripts or cookies until the user
  consents where the law requires it. Load third-party scripts deferred.
- Never send PII (email, name, phone, free text, full URLs containing
  tokens or ids) as event properties. Use opaque ids; strip query strings
  that carry secrets.
- Don't log PII or tokens to the console or to the error tracker; configure
  scrubbing in the SDK (Sentry etc.).
- Anything that stores or sends personal data is a privacy decision, not a
  frontend default — raise it per `nfn-core:engineering-baseline`.

## Feature build order

When the task is a whole feature (not a single component), build in this
order so each step is testable on its own — detail on each step is in the
companions:

1. Contract: the API shape and its schema (`data-and-errors.md`).
2. Types and fetch layer with the query key and error type.
3. Static UI with fixtures for every state: loading, empty, error, full.
4. Wire the data; handle all four states.
5. Interactions and forms (`forms.md`), with accessibility as you go.
6. Tests for the behaviour (`testing.md`); security pass if it touches
   auth, input or redirects (`security.md`).
7. Measure against the budget (`perf.md`) before opening the PR.
