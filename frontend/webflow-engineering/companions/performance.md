# Performance: images, fonts, scripts, interactions

Measure before changing: run PageSpeed Insights or Lighthouse against the
**published** page (not the Designer), mobile profile, and note LCP, INP,
CLS and total weight. Optimise the biggest cost first; change one thing at
a time; re-measure. Targets: LCP ≤ 2.5s, INP ≤ 200ms, CLS ≤ 0.1.

## Images

- Upload at the size you need (not 6000px originals). Prefer **WebP/AVIF**;
  Webflow converts on upload where enabled, but check the output.
- Use **responsive images**: Webflow generates `srcset` for images in
  elements; set `sizes` sensibly. Don't use giant images as CSS
  backgrounds (no srcset, no lazy-load, no alt).
- **LCP image**: set loading to **eager** and give it priority; everything
  below the fold `lazy`. Never lazy-load the hero.
- Always set width/height (or aspect ratio) to prevent layout shift.
- SVG for icons and logos; keep them clean and inline small ones.
- Alt text still required (`accessibility.md`).

## Fonts

- Limit families and weights (each is a request). Prefer variable fonts.
- Self-host or use Webflow's font manager over multiple third-party calls;
  set `font-display: swap`; preload the main text font if it is the LCP.
- Match fallback font metrics to avoid a shift on swap.

## Video and embeds

- No autoplay video with sound; lazy-load YouTube/Vimeo (click-to-load
  facade) and add `loading="lazy"` on iframes below the fold.
- Compress background video, keep it short, provide a poster image, and
  disable it on mobile if it hurts LCP.

## Scripts and custom code

- Every script has a cost. Remove unused ones (old trackers, widgets).
  Load analytics, chat and tag managers **deferred** or after interaction;
  use `defer`/`async` and put non-critical code in the footer, not the
  head. Details and safety rules: `custom-code.md`.
- Page-level scripts only on the pages that need them, not site-wide.
- Avoid heavy libraries for what Webflow does natively.

## Interactions and layout

- Prefer CSS/native interactions to large JS-driven animation; animate
  `transform` and `opacity`, not layout properties.
- Many hidden elements, huge DOM trees, deeply nested wrappers and
  collection lists that render hundreds of items all cost. Paginate or
  limit collection lists (the template limit is not a performance plan).
- Don't load below-the-fold sliders or maps until needed.
- Reduced-motion users get reduced animation (`accessibility.md`).

## Caching and delivery

- Publish to the custom domain over HTTPS; Webflow serves from its CDN.
  Don't add a second CDN layer without a reason.
- After changing assets, confirm the published URL serves the new file
  (cache) before concluding the fix failed.

## Report

Baseline → change → measured result, per item. Say when a change isn't
worth it. Dev/Designer timings are not evidence. If you cannot run a
measurement, say so and give the exact steps for the user to run.
