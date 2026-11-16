---
name: code-review
description: Backend code review — the pre-approval checklist, code smells to flag, when to request changes vs. approve with comments, and whole-codebase reviews. Read when reviewing a backend PR, diff or codebase.
---

# Code review

> Review with rigor and respect. Explain the reasoning, assume good intent, and separate
> what blocks from what doesn't.

This file is the reviewer's lens. The rules being checked live in the companion files, and
each checklist item names its owner.

## 1 · Pre-approval checklist

Check the diff against each item. Don't assume.

- [ ] Errors not swallowed; external data null-checked (`error-handling-logging.md`)
- [ ] No secrets hardcoded or logged (`security.md` §4)
- [ ] Input validated at every boundary; response shape consistent (`security.md` §1, `architecture.md`)
- [ ] No N+1 queries or unbounded loads (`data-layer.md`)
- [ ] Logs have context, no PII, correct level (`error-handling-logging.md` §2)
- [ ] No dead code, `console.log` or `debugger`; existing helpers reused
- [ ] Happy and unhappy paths tested; critical paths at target coverage (`testing.md`)
- [ ] No race conditions on shared values (`data-layer.md` §5)
- [ ] Tokens verified, not decoded; tenant and user from the credential; queries scoped by both (`security.md` §2)
- [ ] Money: provider is the source of truth; each payment applied once; balances changed only conditionally or relatively (`payments-billing.md`)
- [ ] Webhooks: raw-body signature, constant-time compare, event-ID dedupe (`security.md` §8)
- [ ] Server-side fetches of user-supplied URLs are allowlisted or IP-checked (`security.md` §9)
- [ ] No auth bypass reachable on a deployed server (`security.md` §4)
- [ ] Model calls: safety on, all inputs and outputs moderated, per-user limits (`ai-features.md`)
- [ ] Deleting a record deletes its stored files (`security.md` §6)
- [ ] Diff is minimal and scoped to the request; no refactor mixed with a behavior change

## 2 · Smells to flag

- A route handler that validates, computes and persists in one block: split it.
- A service that builds its own DB client: inject it.
- Nested `if`s hiding the error path: use guard clauses.
- Magic numbers, or a function past about 200 lines: name the constant, split the function.
- Hardcoded URLs or config: move them to the config module.

## 3 · Request changes or approve with comments

**Request changes** when the diff has:
- a security issue: hardcoded secret, missing auth or ownership check, injection, unverified token, tenant taken from the request, SSRF, auth bypass
- a money issue: a payment or credit that can apply twice, an amount or plan from the client, a check-then-act on a balance
- a logic error: wrong calculation, race condition, null dereference
- missing tests on a critical path, or a performance problem (N+1, unbounded load, missing index)
- a violation of a standard already established in the codebase
- naming or structure unclear enough to hurt maintainability

**Approve with comments** for: style a formatter would fix, a non-blocking refactor idea, a nice-to-have optimization, or a clarifying comment on code that is already correct.

Every request-changes comment names the specific risk it blocks on. Give the author an
ordered list: what must change, then what's optional.

## 4 · Reviewing a whole codebase

Start by confirming **which branch is deployed**, and compare it with the default branch.
Reviewing a branch nobody runs wastes the review. Record the commit reviewed. Read in risk
order: auth and tenant scoping, money paths, webhooks, outbound requests, file storage and
personal data, then the rest. Give each finding an ID, a severity, the branches it applies
to, `file:line` evidence and a fix, so it can be tracked and re-checked.

## 5 · Tone

Explain *why* a change is needed, not only what. Offer suggestions, not demands. Call out
good patterns, not just problems. Keep feedback focused: a long list of nits buries the one
blocking issue.

## 6 · Done when

- Every checklist item in §1 has been checked against the diff, not assumed
- The author gets a clear, ordered list of what must change versus what is optional
