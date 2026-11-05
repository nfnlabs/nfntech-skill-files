---
name: payments-billing
description: Backend payments, credits and billing — trusting the provider over the client, applying each payment exactly once, atomic balance changes, ledgers, subscription and plan changes, payment and billing webhooks, and admin tools that move money. Read when touching checkout, payment confirmation, credits or usage balances, subscriptions, refunds, or billing webhooks.
---

# Payments, credits and billing

> Money moves exactly once, for the amount the provider says, and only when the provider
> says so.

Webhook signature checks and server-to-server auth → `security.md` §9. Conditional updates,
locks and ledgers at the SQL level → `data-layer.md`. Tests for these paths → `testing.md`.

## 1 · The provider is the source of truth

The client tells you what the user *wants*; the payment provider (Razorpay, Stripe, Shopify
Billing, App Store, Play) tells you what they *paid for*. Never grant from the first.

- Prices, amounts, plan names and credit quantities come from your own catalog or from the
  provider's record — never from the request body.
- Before granting anything, fetch the payment, order, purchase or subscription from the
  provider's API by its ID and check status, amount, currency and that it belongs to this
  customer. A webhook payload or a client "confirm" call is a hint to go and look.
- If the provider has no record, or the record says anything other than paid/active, grant
  nothing — don't fall back to a default period or plan.
- A client-facing "confirm" or "verify" endpoint only triggers that lookup; it never takes
  the plan, amount or status as input.

```js
// Bad — the client names the plan and it is granted
router.post('/billing/confirm', auth, async (req, res) => {
  await activateSubscription(req.tenant, req.body);   // { name: 'growth', ... }
});

// Good — the provider's record decides
router.post('/billing/confirm', auth, async (req, res) => {
  const sub = await billingProvider.getActiveSubscription(req.tenant);
  if (!sub || sub.status !== 'ACTIVE') return res.status(409).json(error('NO_ACTIVE_SUBSCRIPTION'));
  await billingService.applySubscription(req.tenant.id, sub);   // plan from sub, not req.body
});
```

## 2 · Apply each payment exactly once

Payment confirmations arrive more than once: the client calls verify, the webhook fires,
the provider retries, a user replays a request. Every path must be idempotent.

- Give every external payment a unique key in your database (provider payment ID, charge ID,
  subscription period) with a **unique constraint**.
- Grant inside one transaction that first claims the payment:
  `UPDATE payments SET status = 'completed' WHERE id = $1 AND status = 'pending'` — or insert
  the unique charge key — and only adds credits if that changed a row.
- The client verify path and the webhook path call the **same** service function, so the
  second one finds the payment already completed and does nothing.
- Verify signatures (client confirmation and webhook) with `crypto.timingSafeEqual`.

```js
await sequelize.transaction(async (t) => {
  const [claimed] = await Payment.update(
    { status: 'completed', providerPaymentId },
    { where: { id: payment.id, status: 'pending' }, transaction: t },
  );
  if (claimed === 0) return;                       // already applied — do nothing
  await creditService.add(payment.userId, payment.credits, { source: 'payment', ref: payment.id, transaction: t });
});
```

## 3 · Balances and credits

- Spend with a conditional update that refuses to go below zero, **before** doing the paid
  work; refund if the work fails (→ `data-layer.md`, Concurrency).
- Add with a relative update (`balance = balance + n`), never by writing back a value read
  earlier.
- Every change writes a ledger row (who, what, how much, why, reference ID) in the same
  transaction as the balance change. The ledger is append-only.
- Reconcile on a schedule: sum of ledger = balance. Alert on drift; don't silently "fix" it.
- A user with no balance row is not a user with unlimited credit — fail closed.
- Work that runs after the response (background jobs) needs a sweeper that refunds anything
  stuck in "processing" after a restart.

## 4 · Subscriptions and plan changes

- One active subscription per customer, enforced by a unique constraint.
- Activation and renewal lock the billing row and re-check the period inside the transaction,
  so a webhook and a confirm call arriving together grant once.
- Scheduled changes (downgrade at period end, pending upgrade) are applied only after the
  provider confirms the new plan is paid, and are cleared when the customer re-subscribes to
  their current plan.
- Frozen, past-due or cancelled accounts get nothing from scheduled jobs.
- Decide deliberately what happens to unused credits on a plan change, write it down, and
  check it can't be gamed by switching plans back and forth.

## 5 · Tools that move money

Reset, grant, refund and re-sync endpoints are admin tools: behind internal admin auth
(never customer or merchant tokens), audited (who, when, why), and transactional with their
ledger write. A script that grants credits locks the row it changes, the same as the API.

## 6 · Failure modes / anti-patterns to flag

| Anti-pattern | Issue | Fix |
|---|---|---|
| `PUT /subscription` accepts `credits`, `plan` or `status` from the user | free credits | remove, or admin-only |
| Verify endpoint doesn't check `status === 'pending'` | replay credits again | claim with a conditional update |
| Webhook and verify both add credits | one payment counted twice | one idempotent service function |
| Plan or amount read from the request or webhook body | pay for one, get another | read the provider's record |
| No provider record → default 30-day period | free plan without payment | grant nothing |
| `balance = earlierValue + n` | lost updates | relative update |
| Lock taken, released, then balance written later | overspend under concurrency | conditional reserve, refund on failure |
| Ledger row written outside the balance transaction | drift | same transaction |
| Reset/grant endpoint behind merchant auth | self-service free credits | internal admin auth |
| No unique constraint on provider payment ID | duplicates under retries | add the constraint |

## 7 · Done when

- No amount, plan, credit count or status is taken from the client
- Every grant re-checks the provider's record
- Every payment, charge and subscription period has a unique key and is applied once
- Balance changes are conditional or relative, with a ledger row in the same transaction
- Admin money tools use internal auth and are audited
- Integration tests cover replay, concurrent spend and the webhook + confirm race
