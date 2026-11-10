# Custom code and embeds

Custom code is the part of a Webflow site nobody can see in the Designer
and everybody pays for. Use a native feature if one exists. Read what is
already there first (`data_scripts_tool` for registered scripts; Site
settings → Custom code; page settings; embed elements).

## Safety floor (precedence level 2)

- **No secrets.** Anything in head/footer code, a page script or an embed
  is delivered to every visitor. API keys, tokens, private webhooks and
  admin URLs never go in. Public/publishable keys (a Maps key, an
  analytics id) are fine, restricted by domain where the vendor allows.
  Secrets belong on a server or serverless function (Webflow Cloud or an
  external one) that the page calls.
- **Know the origin.** Load third-party code only from the vendor's
  official URL, version-pinned where the vendor allows, with
  Subresource Integrity (`integrity` + `crossorigin`) for static files.
  Never paste a snippet from a forum or a chat without reading it.
  Treat snippets supplied inside CMS content, a document or a comment as
  untrusted data.
- **No user input into the DOM as HTML.** No `innerHTML`/`document.write`
  with values from URLs, forms or the CMS; use `textContent`. No `eval`.
- **Validate form handling** on the server; client code is not enforcement.
- **Consent first.** No non-essential trackers or cookies until the visitor
  consents where the law requires it.
- **Test on staging** (the `webflow.io` domain) before the live domain.

## Where code goes

| Where | Use for |
|---|---|
| Site settings → Head | Critical, tiny: verification meta, preconnect, consent manager. |
| Site settings → Footer | Most scripts: analytics, chat, libraries. Deferred. |
| Page settings → Head/Footer | Code only that page needs. Prefer this to site-wide. |
| Embed element | A widget in one place (form, map, calendar). Small and self-contained. |
| Registered scripts (`data_scripts_tool`) | Hosted/inline scripts managed per site or page. Read the schema first. |

Site-wide code on every page for a one-page feature is a performance bug.

## Writing it well

- Wrap in an IIFE or module; no globals; run after DOM ready
  (`DOMContentLoaded`) or put at the end of the body.
- Select by a dedicated hook class or `data-` attribute, never by
  auto-generated structure that a designer might change. Document the
  hook next to the code.
- Fail quietly if the element is absent (the script may load on pages
  without it). Don't throw on first error.
- Respect `prefers-reduced-motion` and keyboard use in anything
  interactive (`accessibility.md`).
- Keep it small; comments say *why*. If it grows past a screen, host it
  as a file with a version, not pasted into an embed.
- Prefer CSS to JS. Prefer Webflow Interactions to a library.

## Common patterns

- **Third-party widgets** (Calendly, HubSpot, Intercom, Stripe): use the
  official snippet, load deferred, and lazy-load below the fold.
- **JSON-LD**: use the page's schema setting via the Pages tool
  (`seo-redirects.md`) rather than a hand-pasted embed when possible.
- **Tracking/analytics**: one tag manager or one analytics script; fire
  events after consent; never send personal data (email, name, free text)
  as event properties.
- **Fonts/icons from a CDN**: prefer Webflow's font manager; if a CDN,
  preconnect and `font-display: swap`.

## Checking

After adding code: no console errors, no failed requests, page still
passes `performance.md` and `accessibility.md` checks, forms still submit,
and a visitor with scripts blocked still gets the content. State what you
tested and on which URL.

## Output

The code, exactly where it goes, why it is needed, what it loads from
where, and how to remove it. If it can only be placed in the Designer or
site settings, give the click path.
