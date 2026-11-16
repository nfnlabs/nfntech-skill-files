---
name: ai-features
description: Backend features built on AI models (LLMs, image generation, vision, moderation) — content safety, cost and abuse limits, background jobs, data handling, prompt and model versioning, and testing. Read when adding or changing anything that calls a model or stores its output.
---

# AI features

> Treat every model call as untrusted, slow and expensive. Check what goes in and what comes
> out, never make a request wait on it, and never let one user spend without limit.

Rate-limit policy → `security.md` §7. Fetching user-supplied image URLs → `security.md` §9.
Credits that pay for calls → `payments-billing.md`.

## 1 · Content safety

- Keep provider safety settings at their defaults or stricter. Turning a category to "block none" needs a written reason and a replacement check.
- Moderate **every** user-controlled input (uploaded photos, other images, URLs, text), and moderate the **output** before storing or showing it. Checking only one input leaves the others as a bypass.
- Features that generate images of people need explicit rules against sexualized or harmful imagery of real people, enforced in code, not only in the prompt.
- Store why content was blocked (category, which input) so false positives can be reviewed. Show users a plain message, not the provider's raw reason.

## 2 · Cost and abuse

- Reserve or charge credits **before** the call, and refund on failure (`payments-billing.md`).
- Rate-limit every model-backed endpoint per user and per tenant, keyed on the authenticated identity. Add a daily spend cap with an alert.
- Cap input size before sending anything: image dimensions and bytes, prompt length, image count.
- Record tokens, images and cost per call against the user and feature, so spend can be traced and reconciled.

## 3 · Latency: model calls are background jobs

Generation and validation take seconds to minutes. Don't hold an HTTP request open for them.

- Accept the request, reserve credits, enqueue the job, and return `202` with a job ID. The client polls a status endpoint scoped to the owner, or gets a push.
- Use a durable queue (SQS, BullMQ, a jobs table). `setImmediate` or an unawaited promise is lost on restart. If you must use one, add a sweeper that fails and refunds jobs stuck in "processing."
- Set a timeout on every provider call and on every download of its output.
- Retry only transient errors, with backoff and a cap. Never retry a safety block.

## 4 · Data handling

- Don't log prompts, images, signed URLs or personal model output. Log the job ID, model, token counts, duration and outcome (`security.md` §4).
- Know each provider's retention and training policy, and choose settings and providers that match your privacy promises.
- Generated images of a person are personal data. They follow the same deletion and retention rules as the uploads they came from.
- Send API keys in headers, never in query strings (`?key=`). Query strings end up in logs and error reports.

## 5 · Prompts, models and config

- Keep prompts, model names and thresholds in versioned config or code, not scattered string literals. Record the prompt version with each result.
- Pin model versions. Treat an upgrade like a dependency upgrade, and test it on a fixed sample set first.
- Remove unused providers and code paths. Dead providers keep live keys and attack surface.

## 6 · Testing

- Unit-test everything around the model (input checks, prompt building, response parsing, credit reserve and refund), with the provider mocked at its HTTP boundary.
- Keep a small fixed evaluation set (inputs plus expected output properties). Run it before changing prompts, models or thresholds.
- Test the failure paths: timeout, safety block, malformed response, empty output. Each must refund and leave the job in a final state.

## 7 · Done when

- Every user input and every output is moderated; safety settings are not weakened
- Model calls run as background jobs with timeouts; failures refund credits
- Per-user limits and a spend cap protect every model-backed endpoint
- No prompts, images, signed URLs or keys in logs; prompt and model versions are recorded with results
