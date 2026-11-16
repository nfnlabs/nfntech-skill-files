---
name: payments-billing
description: Backend payments, credits and billing — trusting the provider over the client, applying each payment exactly once, atomic balance changes, ledgers, subscriptions and plan changes, billing webhooks, and admin money tools. Read when touching checkout, payment confirmation, credits, subscriptions, refunds or billing webhooks.
---

# Payments, credits and billing

> Money moves exactly once, for the amount the provider reports, and only when the provider
> says so.

Webhook signatures and server-to-server auth → `security.md` §8. Conditional updates and
ledgers at the SQL level → `data-layer.md` §5. Tests for these paths → `testing.md` §4.

## 1 · The provider is the source of truth

The client says what the user *wants*. The provider (Razorpay, Stripe, Shopify Billing, App
Store, Play) says what they *paid for*. Grant only from the second.

- Prices, plan names and credit quantities come from your own catalog or the provider's record, never from the request body.
- Before granting, fetch the payment, order, purchase or subscription by ID from the provider's API. Check status, amount and currency, and check that it belongs to this customer. A webhook payload or a client "confirm" call is a reason to look, not proof.
- No provider record, or a status other than paid or active: grant nothing. Don't fall back to a default period or plan.
- A client "confirm" or "verify" endpoint only triggers the lookup. It never takes plan, amount or status as input.

```js
// Bad: the client names the plan                  // Good: the provider's record decides
await activateSubscription(req.tenant, req.body);  const sub = await billingProvider.getActiveSubscription(req.tenant);
                                                   if (sub?.status !== 'ACTIVE') return res.status(409).json(error('NO_ACTIVE_SUBSCRIPTION'));
                                                   await billingService.applySubscription(req.tenant.id, sub); // plan from sub, not req.body
```

## 2 · Apply each payment exactly once

Confirmations arrive more than once: client verify, webhook, provider retry, user replay.
Every path must be idempotent.

- Give every external payment a unique key (provider payment ID, charge ID, subscription period) under a unique constraint.
- Claim the payment inside a transaction. Credit only if the claim changed a row:

```js
await sequelize.transaction(async (t) => {
  const [claimed] = await Payment.update(
    { status: 'completed', providerPaymentId },
    { where: { id: payment.id, status: 'pending' }, transaction: t },
  );
  if (claimed === 0) return;                       // already applied
  await creditService.add(payment.userId, payment.credits, { source: 'payment', ref: payment.id, transaction: t });
});
```

- The verify path and the webhook path call the **same** service function. The second call finds the payment already completed and does nothing.
- Verify signatures on both the client confirmation and the webhook with `crypto.timingSafeEqual`.

## 3 · Balances, credits and ledger

- Spend with a conditional update that can't go below zero, **before** the paid work starts. Refund if the work fails (`data-layer.md` §5).
- Add with a relative update, never by writing back a value read earlier.
- Each change writes an append-only ledger row (who, what, how much, why, reference ID) in the same transaction as the balance change.
- Reconcile on a schedule: the ledger sum must equal the balance. Alert on drift, and don't silently "fix" it.
- No balance row means zero credit. Fail closed.
- Background work that runs after the response needs a sweeper that refunds anything stuck in "processing" after a restart.

## 4 · Subscriptions and plan changes

- One active subscription per customer, enforced by a unique constraint.
- Activation and renewal lock the billing row and re-check the period inside the transaction, so a webhook and a confirm call arriving together grant once.
- Scheduled changes (downgrade at period end, pending upgrade) apply only after the provider confirms the new plan is paid. Clear them when the customer re-subscribes to their current plan.
- Frozen, past-due and cancelled accounts get nothing from scheduled jobs.
- Decide what happens to unused credits on a plan change. Write it down, and check that switching plans back and forth can't game it.

## 5 · Admin money tools

Reset, grant, refund and re-sync endpoints and scripts sit behind internal admin auth (never
customer or merchant tokens), are audited (who, when, why), and write their ledger row in
the same transaction as the change. A script that grants credits locks the row, the same as the API does.

## 6 · Done when

- No amount, plan, credit count or status is taken from the client
- Every grant re-checks the provider's record
- Every payment, charge and subscription period has a unique key and is applied once
- Balance changes are conditional or relative, with a ledger row in the same transaction
- Integration tests cover replay, concurrent spend and the webhook-plus-confirm race
