# Building frontend code

The target is code that looks like it came from someone who works in this
codebase every day, rather than something assembled from a tutorial.

## Structural decisions

**Props and composition.** Prefer `children` and slots over configuration
props. A fourth boolean prop usually means there are two components here.

**Forms.** Past three fields, use the project's form library or
uncontrolled inputs with `FormData`. Eight `useState` calls for eight
inputs is a smell.

**Styling.** Use the project's scale tokens over arbitrary values unless
the design genuinely demands one. Conditional classes go through
`cn()`/`clsx` rather than inline ternary string concatenation. Repeated
class strings become a component.

## What to avoid, concretely

- Comments restating the code. Comment non-obvious *why* only.
- Placeholder gaps: `// ... rest of your component`, `// your logic here`.
  Ship the file, or say which part you're showing.
- Scaffolding nobody asked for — try/catch everywhere, `?.` on values that
  can't be null, loading and error states on a static component.
- `useMemo`/`useCallback`/`React.memo` by default. They cost something;
  add them when there's a reason and name it. If the React Compiler is
  enabled, most manual memoisation is redundant.
- Premature abstraction: a `utils/` helper with one call site, a generic
  wrapper used once, a hook wrapping a single `useState`.
- Wrapper `div` soup. Use fragments; let the parent own layout.
- Inventing an API shape, env var, or design token that wasn't specified.
  Ask, or make the seam obvious and flag it in a line.
- Emoji in UI copy or code unless the project already uses them.

## Output

1. One or two lines: what you built, and any assumption you had to make.
2. The code — complete, runnable, in the project's language and layout.
3. Only if it's real: one note about a trade-off worth overriding.
