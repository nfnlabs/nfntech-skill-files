---
name: code-review
description: Backend code review — the pre-approval checklist, anti-patterns to flag, and when to request changes vs. approve with comments. Read when reviewing a backend PR or diff.
---

# Code review

> Review with respect but rigor. Catch issues early, explain the reasoning, and assume good
> intent.

The underlying rules being checked against live in `architecture.md`, `data-layer.md`,
`security.md`, `error-handling-logging.md`, and `testing.md` — this file is the reviewer's
lens on all of them.

## 1 · Pre-approval checklist

- [ ] No swallowed errors or silent failures
- [ ] All external data (API/DB/SDK) null-checked before use
- [ ] No secrets/keys hardcoded or logged
- [ ] Input validated at every boundary (params, query, body)
- [ ] Consistent API response shape
- [ ] No N+1 queries or unbounded collection loads
- [ ] Logging includes context, no PII/secrets, correct level
- [ ] No dead code, leftover debug logs, or stray `console.log`
- [ ] Existing helpers reused instead of duplicated
- [ ] Tests cover happy path **and** unhappy paths, ≥80% on critical paths
- [ ] No obvious race conditions or concurrency issues
- [ ] Third-party identity tokens verified, not decoded; tenant/user taken only from the credential
- [ ] Every query on a tenant's data scopes by tenant and owner
- [ ] Money and credits: amounts and plans from the provider, not the client; each payment
      applied once; balances changed by conditional/relative updates (→ `payments-billing.md`)
- [ ] Webhooks: raw-body signature, constant-time compare, event-ID dedupe
- [ ] Server-side fetches of user-supplied URLs are allow-listed or IP-checked
- [ ] No auth bypass reachable in a deployed environment
- [ ] Model calls: safety settings on, inputs and outputs moderated, per-user limits (→ `ai-features.md`)
- [ ] Deleting a record deletes its stored files
- [ ] Diff is minimal and scoped to the request

## 2 · What to look for, by area

**Single responsibility.** Each function/class has one reason to change — flag a route
handler that validates, computes, and persists in one block.

**Dependency injection.** A service that instantiates its own DB client is tightly coupled
and hard to test; it should receive dependencies through its constructor.

**Fail fast.** Nested `if`s hiding the error path should become guard clauses.

**Meaningful errors.** `throw new Error('Failed')` gives a reviewer and an on-call engineer
nothing — it should carry the relevant ID and the underlying cause.

## 3 · Anti-patterns to flag

| Anti-pattern | Issue | Fix |
|---|---|---|
| Silent error swallowing | `try { ... } catch (e) {}` | log and re-throw or handle explicitly |
| Mixing async patterns | callbacks + Promises + async/await | use async/await consistently |
| Hardcoded config | `const url = 'http://...'` | environment variable via config module |
| Unbounded queries | `User.find()` with no limit | add pagination or a limit |
| Missing null checks | `user.email` when `user` might be null | check before use |
| Magic numbers | `if (x > 100)` | extract to a named constant |
| God functions | 200+ line handler | split into smaller functions |
| Tight coupling | service instantiates its own dependencies | inject dependencies |
| No error context | `throw new Error('Failed')` | include relevant IDs and state |
| Leftover debug code | `console.log`, `debugger` | remove before merge |

## 4 · When to request changes

- Security issue: hardcoded secret, missing auth check, injection risk, unverified identity
  token, tenant taken from the request, SSRF, auth bypass flag
- Money issue: a payment or credit that can apply twice, a plan or amount trusted from the
  client, a check-then-act on a balance
- Logic error: wrong calculation, race condition, null dereference
- Test coverage missing for a critical path
- Performance issue: N+1 query, unbounded load, missing index
- Violates a project standard already established elsewhere in the codebase
- Naming or structure unclear enough to impact maintainability

## 5 · When to approve with comments

- Minor style inconsistency that auto-formatting would fix
- A suggestion for a future refactor that isn't blocking
- A nice-to-have optimization that isn't critical
- A clarifying comment would help, but the code is correct as written

## 6 · Reviewing a whole codebase

A full review (not a diff) starts by confirming **which branch is deployed** and comparing it
with the default branch — reviewing a branch nobody runs wastes the review. Record the commit
reviewed. Then read in risk order: authentication and tenant scoping, money paths, webhooks,
outbound requests, file storage and personal data, then the rest. Give each finding an ID,
a severity, the branches it applies to, `file:line` evidence and a fix, so it can be tracked
and re-checked.

## 7 · Tone

Be respectful and assume good intent. Explain *why* a change is needed, not just *what* to
change. Offer suggestions, not demands. Call out good patterns, not only problems. Keep
feedback focused and actionable — a long list of nits buries the one blocking issue.

## 8 · Done when

- Every checklist item in §1 has been checked against the diff, not assumed
- Every request-changes comment names the specific risk (security, correctness, coverage,
  performance) it's blocking on
- The review leaves the author with a clear, ordered list of what must change vs. what's
  optional
