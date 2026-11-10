# Forms and validation

A form has two jobs: collect input a user can fix, and deliver data a
server can trust. The second is never the client's job alone — client
validation is UX, server validation is enforcement. Write the rules once
and run them in both places.

## Read the project first

`grep -n "zod\|react-hook-form\|valibot\|@conform\|formik" package.json`
and look at one existing form. Match its library and error display. Check
the installed React/Next majors: `useActionState`, form actions and
`useFormStatus` (from `react-dom`) are **version-dependent** — React 19
and recent Next.js. `useActionState` was previously `useFormState`.

## One schema, both sides

Define the schema in a module with no browser or server imports, so both
can import it:

```ts
// features/profile/schema.ts
import { z } from 'zod'

export const profileSchema = z.object({
  displayName: z.string().trim().min(1, 'Enter a name').max(80),
  email: z.string().trim().email('Enter a valid email'),
  marketing: z.literal('on').optional(),   // unchecked checkbox is simply absent
})
export type ProfileInput = z.infer<typeof profileSchema>
```

*(zod 3 syntax shown. zod 4 changes the API: custom messages use
`{ error: '…' }` instead of `errorMap`, string formats are top-level
(`z.email()`; `.email()` is deprecated), and `error.flatten()` is
deprecated in favour of `z.flattenError(error)` (check the installed
version for which still work). Read the installed major first —
SKILL.md §2 — and use that major's form.)*

- The client runs it for instant feedback (via the form library's resolver,
  or on blur/submit).
- The server runs it again, on the raw input, inside the action or handler
  — always. A client that "already validated" proves nothing.
- Business rules that need the database ("email already taken") exist only
  on the server and come back as field errors.
- Normalise in the schema (`trim`, lowercase email), not scattered.

## Choosing the mechanism

| Form | Use |
|---|---|
| ≤ 3 fields, server mutation, Next App Router | A `<form action={serverAction}>` with `useActionState`; works without JS |
| Many fields, dependent fields, field arrays, rich client UX | React Hook Form + the zod resolver (uncontrolled inputs, few re-renders) |
| Sends to a separate REST API from a SPA | RHF (or `FormData`) + a TanStack Query mutation |

Past three fields, don't use one `useState` per input (`build.md`).

## `useActionState` pattern *(version-dependent)*

An authenticated action (excerpt — `requireUser`, `saveProfile` and the
`/profile` path are the project's own):

```tsx
// features/profile/actions.ts
'use server'
import { revalidatePath } from 'next/cache'
import { profileSchema } from './schema'

export type FormState =
  | { status: 'idle' }
  | { status: 'error'; fieldErrors: Record<string, string[] | undefined>;
      values: Record<string, string>; message?: string }
  | { status: 'success' }

export async function updateProfile(_prev: FormState, formData: FormData): Promise<FormState> {
  const user = await requireUser()             // authenticate first — security.md
  const raw = Object.fromEntries(formData) as Record<string, string>
  const parsed = profileSchema.safeParse(raw)
  if (!parsed.success) {
    // echo back only the named, non-secret fields so the form keeps them —
    // never `raw` wholesale (it would include passwords, files and $ACTION_* keys)
    return {
      status: 'error',
      fieldErrors: parsed.error.flatten().fieldErrors,
      values: { displayName: raw.displayName ?? '', email: raw.email ?? '' },
    }
  }
  await saveProfile(user.id, parsed.data)      // scoped to the caller, not to an id from the form
  revalidatePath('/profile')                   // what this changes — data-and-errors.md
  return { status: 'success' }
}
```

```tsx
// features/profile/profile-form.tsx
'use client'
import { useActionState } from 'react'
import { updateProfile, type FormState } from './actions'

const initial: FormState = { status: 'idle' }

export function ProfileForm() {
  const [state, formAction, pending] = useActionState(updateProfile, initial)
  const values: Record<string, string> = state.status === 'error' ? state.values : {}
  return (
    <form action={formAction} noValidate>
      <label htmlFor="displayName">Name</label>
      <input id="displayName" name="displayName" defaultValue={values.displayName} />
      {/* error text, aria-describedby and aria-invalid per the UX list below */}
      <button disabled={pending}>{pending ? 'Saving…' : 'Save'}</button>
    </form>
  )
}
```

A **public** action (signup, login, reset, contact) follows the same shape
but skips `requireUser()` — it has no session yet. It validates with the
schema, rate-limits, and returns generic errors that don't reveal whether
an account exists (`security.md` → "Authentication itself").

Two `FormData` traps: `Object.fromEntries` keeps only the *last* value of a
repeated key, so use `formData.getAll('tags')` for checkbox groups and
multi-selects; and the entries include framework-internal `$ACTION_*`
keys, which is why the schema should strip unknown keys (zod's default) and
not be `.strict()`.

- Return validation failures as **data**; throw only for the unexpected
  (that goes to `error.tsx`).
- Return the submitted values on error (without passwords) so the form
  doesn't wipe what the user typed — uncontrolled inputs reset after an
  action unless you set `defaultValue` from state.
- `redirect()` throws; call it outside `try/catch`, last.
- Disable the submit button while pending to prevent double submits, and
  make the mutation idempotent on the server where it matters.

## Field-level UX and accessibility

- Every input has a visible `<label htmlFor>`; a placeholder isn't a
  label. Use the right `type`, `inputMode`, `autoComplete` and `name`.
- Errors render next to the field, linked with `aria-describedby`, with
  `aria-invalid="true"`; colour is never the only signal. Mark required
  fields in text, not just a red asterisk.
- On a failed submit, move focus to the first invalid field or to an
  error summary with links. Announce server errors in an `aria-live`
  region (`role="alert"`).
- Validate on blur and on submit; don't flash errors on the first
  keystroke. Once a field has errored, revalidate on change.
- Use native constraints (`required`, `type=email`) for the free baseline
  but set `noValidate` and own the message so it's consistent.
- Don't disable submit just because the form is invalid — users can't tell
  why. Show the errors instead.
- Preserve data on navigation away only if it's long; warn on unsaved
  changes for long forms.
- WCAG 2.2: don't block paste, autofill or password managers (Accessible
  Authentication), don't make users retype information they already gave
  in the same flow (Redundant Entry), and give anything drag-based a
  click or keyboard alternative.

## Submit states

Idle, pending, success, error — each handled. Success says what happened
and where the user goes next (toast alone is easy to miss; confirm inline
or redirect). Error keeps the user's input and offers retry. Network
failure is different from validation failure: don't show "fix your input"
for a 500.

## What not to do

- Validating only in the client, or only in the server.
- Writing the zod schema and a separate TypeScript interface; infer.
- Trusting a hidden field, `disabled` state or a price/role sent by the
  client — recompute on the server.
- Sending passwords or tokens back in an error state, a URL, or a log.
- File inputs without server-side type/size checks (`security.md`).
- Stacking `useEffect`s to sync form state — derive or use the form
  library.

## Tests

Test the schema as a unit (valid, each invalid branch, normalisation) and
the form as a component: fill by label, submit, assert the visible error
and that the success path calls the mocked endpoint (`testing.md`).
