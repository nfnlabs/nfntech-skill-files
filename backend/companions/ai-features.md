---
name: ai-features
description: Backend features built on AI models (LLMs, image generation, vision, moderation) — content safety on inputs and outputs, cost and abuse limits, running model calls as background jobs, keeping prompts, images and personal data out of logs, provider keys, and testing model-backed code. Read when adding or changing anything that calls an AI model or stores what one generates.
---

# AI features

> Treat every model call as untrusted, slow and expensive: check what goes in and what comes
> out, never make a user wait on it inside a request, and never let one user spend without
> limit.

Rate limiting mechanics → `security.md` §7 and `performance-deployment.md`. Fetching image
URLs that users send → `security.md` §10. Credits that pay for model calls →
`payments-billing.md`.

## 1 · Content safety

- Keep the provider's safety settings at their defaults or stricter. Turning a category to
  "block none" needs a written reason and a replacement check.
- Moderate **every** input a user controls — the photo they upload *and* any other image,
  URL or text they pass in — and moderate the **output** before you store or show it.
  Checking only one input leaves the others as a way around it.
- Features that generate images of people need explicit rules against sexualised or
  harmful imagery of real people, enforced in code, not only in the prompt.
- Store why something was blocked (category, which input) so false positives can be
  reviewed; show the user a plain message, not the provider's raw reason.

## 2 · Cost and abuse

Every model call costs money, so an unprotected endpoint is a way to spend yours.

- Charge or reserve credits **before** the call, refund on failure (→ `payments-billing.md`).
- Per-user and per-tenant rate limits on every model-backed endpoint, keyed on the
  authenticated identity, plus a daily spend cap with an alert.
- Cap input sizes (image dimensions and bytes, prompt length, number of images) before
  sending anything.
- Record tokens, images and cost per call against the user and feature, so spend can be
  traced and reconciled.

## 3 · Latency: model calls are background work

Generation and validation calls take seconds to minutes. Don't hold an HTTP request open for
them.

- Accept the request, reserve credits, enqueue the job, return `202` with a job ID; the
  client polls a status endpoint (scoped to the owner) or gets a push.
- Use a durable queue (SQS, BullMQ, a jobs table). `setImmediate` or an unawaited promise is
  lost on restart; if you use one, add a sweeper that fails and refunds jobs stuck in
  "processing".
- Set a timeout on every provider call and on every download of a provider's output.
- Retry only transient errors, with backoff and a cap; never retry a safety block.

## 4 · Data handling

- Don't log prompts, images, image URLs (signed URLs are credentials), or model output that
  contains personal data. Log the job ID, model, token counts, duration and outcome.
- Know what each provider does with your inputs (training, retention) and choose settings
  and providers that match your privacy promises.
- Generated results are personal data when they show a person: they follow the same
  deletion and retention rules as the uploads they came from.
- Send API keys in headers, not URL query strings (`?key=`), so they don't end up in logs
  or error reports.

## 5 · Prompts and configuration

- Keep prompts, model names and thresholds in versioned config or code, not scattered string
  literals, and record which prompt version produced each result.
- Pin model versions; treat a model upgrade like a dependency upgrade — test it on a fixed
  sample set before switching.
- Remove providers and code paths that are no longer used; dead providers keep their keys,
  their attack surface and their confusion.

## 6 · Testing

- Unit-test everything around the model (input checks, prompt building, response parsing,
  credit reserve and refund) with the provider mocked at its HTTP boundary.
- Keep a small fixed evaluation set (inputs plus expected properties of the output) and run
  it before changing prompts, models or thresholds.
- Test the failure paths: timeout, safety block, malformed response, empty output — each
  must refund and leave the job in a final state.

## 7 · Failure modes / anti-patterns to flag

| Anti-pattern | Issue | Fix |
|---|---|---|
| Safety categories set to `BLOCK_NONE` | harmful content generated under your name | defaults or stricter |
| Only the user's photo is moderated | other inputs bypass the check | moderate every input and the output |
| Model call awaited inside the HTTP request | timeouts after cost is paid; workers tied up | background job + status endpoint |
| No per-user limit on a model-backed endpoint | unbounded spend | rate limit + spend cap |
| Signed image URL or prompt in logs | private data exposed | log IDs only |
| API key in `?key=` | key leaks into logs and error trackers | header |
| Six providers, one in use | dead code with live keys | remove unused paths |

## 8 · Done when

- Every user-controlled input and every output is moderated; safety settings not weakened
- Model calls run as background jobs with timeouts, and failures refund credits
- Per-user limits and a spend cap protect every model-backed endpoint
- No prompts, images, signed URLs or keys in logs
- Prompt and model versions are recorded with each result
