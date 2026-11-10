# SEO settings and redirects

Read first: `list_pages`, then `get_page_metadata` for the pages in play,
and the site's domain and locale setup. Writes go through
`update_page_settings` / `bulk_update_pages` (up to 100 pages per call).

## Per page

| Item | Rule |
|---|---|
| Title tag | Unique, front-loaded keyword, brand last. Roughly 50–60 characters; judge by the SERP, not a hard cut. |
| Meta description | Unique, written for a click, roughly 120–160 characters. Not a copy of the first paragraph. |
| `h1` | Exactly one, matches the page topic. |
| Open Graph | `og:title`, `og:description`, and an image (1200×630) via `imageAssetId` or `imageUrl`. |
| Slug | Short, lowercase, hyphenated. **Changing a published slug breaks links and rankings** — pair it with a 301. |
| Indexing | Staging, thank-you, utility and duplicate pages are noindex; check the page setting rather than assuming. |
| Canonical | Set where the same content lives at two URLs (filters, locale, print). |

Collection pages: bind the SEO title, description and OG image to CMS
fields (`cms-design.md`) so each item is unique.

## Schema markup (JSON-LD)

Use `bulk_update_pages_schema_markup` (1–25 pages) and read back with
`query_pages_schema_markup`. Only mark up what is true and visible on the
page: `Organization`, `Article`/`BlogPosting`, `BreadcrumbList`, `FAQPage`,
`Product`, `LocalBusiness`. Valid JSON, absolute URLs, no invented ratings
or prices. Validate with the Rich Results Test after publishing.

## Sitemap, robots, locales

- The auto sitemap lists published pages and CMS items; exclude pages that
  shouldn't be indexed. Submit it in Search Console.
- `robots.txt` lives in site settings (Designer/dashboard): never
  `Disallow: /` on production; disallow staging by hosting it on the
  webflow.io domain with indexing off.
- Multilingual sites: set per-locale titles, descriptions and slugs
  (`localeId`) and `hreflang`; don't leave a secondary locale on the
  primary's metadata.

## 301 redirects

Redirects live in Site settings → Hosting → 301 redirects (check
`data_sites_tool` / other tools for an API before saying it's Designer-only).
When you cannot create them, produce a table the user can paste.

- Redirect **old path → new path**, one hop, 301. No chains, no loops, no
  redirect to a redirect.
- Needed whenever a slug, folder or domain changes, a page is deleted, or
  a site migrates in. Map each old URL to its closest new equivalent; use
  the homepage only as a last resort.
- Webflow redirects match paths (and wildcards on supported plans);
  confirm the syntax in the current docs before bulk-pasting.
- After publish, test a sample of old URLs return 301 to a 200.

## Content hygiene

- Internal links use relative paths or the live domain, never the
  `webflow.io` staging URL.
- Link text is descriptive. Images have alt text (`accessibility.md`).
- Heading order is logical; one `h1`.
- Don't stuff keywords; write for the reader.

## Output

A table of page → title / description / OG / indexing / canonical changes,
the schema blocks written, the redirect map (old → new), and what the user
must do in settings. State what you did not verify (live indexing, SERP
appearance).
