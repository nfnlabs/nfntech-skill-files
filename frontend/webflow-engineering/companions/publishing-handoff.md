# Publishing, staging, backups and handoff

Publishing is outward-facing: it changes what the public sees and it can't
be quietly undone. Never publish without an explicit ask in this
conversation, and an earlier approval doesn't carry to a later publish.

## What publishing does

- **Publish site** (`publish_site`) pushes design, pages and published CMS
  items to the chosen domains. One publish per site per minute.
- **Publish CMS items** (`publish_collection_items`) pushes only those items;
  it does **not** publish design or template changes. The reverse is also
  true: a site publish doesn't publish draft items.
- **Single-page publish** (`pageId`) needs an Enterprise site with the
  feature enabled and a prior full publish; CMS items aren't included.
- **Staging** is the `webflow.io` subdomain. Publish there first
  (`publishToWebflowSubdomain: true`, no `customDomains`), review, then
  publish to the custom domain. Page branches (Enterprise) preview a page
  without touching main: `create_branch` → work → `publish_branch` (staging
  only) → `merge_branch`; resolve conflicts explicitly.
- `unpublish_collection_items` returns items to draft, the clean undo for a
  premature item publish. Un-publishing a site is a dashboard action.

## Pre-publish gate

Only after every item passes, and the user asked:

1. Content: CMS items verified against their source (read-back for
   imports, `cms-import-docx.md`); no placeholder text; drafts you did not
   mean to ship are still drafts.
2. Pages: unique titles/descriptions, Open Graph, canonical, noindex only
   where intended, 301s ready (`seo-redirects.md`).
3. Accessibility pass on key templates (`accessibility.md`).
4. Performance pass against the budget (`performance.md`).
5. Custom code reviewed and tested on staging (`custom-code.md`).
6. Forms submit to the right place and send a notification; thank-you
   state works.
7. Responsive check at every breakpoint; links work; no `webflow.io` URLs
   in content.
8. **Backup exists** (below).
9. State in one sentence what will go live and where.

After publishing: load the live URL, check a sample of changed pages and
one CMS item, and confirm the redirects. Report what you checked.

## Launch checklist (whole-site sequence)

`styling-system.md` → `cms-design.md` → content/imports → `seo-redirects.md`
→ `accessibility.md` → `performance.md` → `custom-code.md` → this file.
Domain: DNS records (A/CNAME) set at the registrar, SSL provisioned, www
and non-www redirect to one canonical host, old site redirected with 301s,
Search Console and analytics verified.

## Backups

- Webflow keeps site **backups** and a saved version history in Site
  settings → Backups; create a named backup immediately before a risky
  change or launch. Check whether any tool exposes this before claiming it
  is Designer-only.
- CMS: export each collection to CSV before bulk edits, imports or
  deletes; keep the file with the project. The audit trail from an import
  (`coverage.json`, `verify_report.md`) is also evidence.
- Restoring is a deliberate act: it can overwrite newer work. Confirm
  before restoring, and never restore on a live site without a fresh
  backup of the current state.

## Client handoff

Hand over when the site is launched and verified, not before.

- **Ownership and access**: site in the client's Workspace or transferred;
  client has Admin on the site; our access reduced to what's agreed.
  Hosting, domain registrar, DNS and analytics accounts in the client's
  name. Ownership transfers and billing are dashboard actions.
- **Roles**: Editors for content (Editor can't change design). Use the
  Editor for content so clients can't break structure.
- **Documentation** (short, in the client's words): how to edit each CMS
  collection, field-by-field notes (help text carries this too), how to
  add a blog post, how to change images and keep alt text, what not to
  touch, how to publish.
- **Style guide**: the class system and variables used, component list, and
  where custom code lives.
- **Training**: a recorded walkthrough (Loom) of the editing tasks.
- **Support**: what's covered, response times, how to request changes.
- **Recovery**: where backups are, who can restore, how redirects were
  handled, the list of third-party services and renewal dates.
- Remove staging passwords/test users and dev notes; rotate any shared
  credentials.

## Output

State exactly what was published and where, what you verified afterwards,
what needs the dashboard (billing, domain, roles, backup restore), and a
handoff checklist with each item marked done or open. Don't say a launch is
complete if a gate item is open.
