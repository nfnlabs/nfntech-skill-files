# Stage 6c — reviewing how the imported content actually renders

Correct data and a correct page are different claims. This stage checks the
second one. Work through it in order and stop at the first failure that would
make the rest meaningless (an unbound field makes styling questions moot).

## 1. Find the pages that display the collection

`data_pages_tool` → `list_pages` for the site. You are looking for:

- the **collection template page** for this collection (one page per item), and
- any **static page with a Collection List** bound to it (index, homepage
  section, related-items list).

If several template pages exist for the collection, check the one the items'
URLs resolve to.

## 2. Confirm every imported field is actually bound to something

`data_element_tool` → query the template page's element tree. For each field you
wrote, find the element bound to it. Then compare the two lists:

- **Written but not bound** — the content is in the CMS and invisible on the page.
  This is the most common outcome of an import into an older template and worth
  raising immediately: either the template needs an element bound to that field,
  or the field did not need populating.
- **Bound but empty** — an element expects a field the documents did not supply
  (no Summary section, no image). On the page this shows as an empty block or a
  collapsed card. Say which items are affected.

Note the element's tag for each rich-text binding. If the rich-text block sits
inside a container that already provides an `h1`, confirm `heading_shift` put the
document's headings below it.

## 3. Read the rendered markup of one published item

Once at least one item is published, fetch its live URL and check the region
that came from the rich-text field:

- Headings appear at the intended levels, one `h1` on the page.
- Lists render as `ul`/`ol`, not as paragraphs that begin with "1." — the latter
  means the source used typed-in numbering and it was not detected.
- No visible tag text (`<strong>`), which would mean HTML went into a PlainText
  field.
- No doubled or missing space around bold and linked phrases — read a couple of
  sentences that contain inline formatting, since this is where Word damage shows.
- Images have the alt text that came from the document (or are intentionally empty).
- Links resolve and are absolute.
- Any table is legible, not a column of unstyled text.

Fetching the page is also the only check that the CDN is serving the new content;
a published item that still shows old text means the site itself needs publishing.

## 4. Check the collection list, not just the detail page

On the index or listing page:

- Excerpt text fits its card, and truncation happens where the design expects it
  rather than mid-word.
- Sort order is what the person expects — imports commonly land with identical
  dates, so a date sort shows an arbitrary order. If dates came from documents,
  confirm they varied.
- Items intended as drafts do not appear.
- Item count matches what was imported plus what was already there.

## 5. Report

Two lists, kept short, with the distinction that matters to the person:

**Content issues (fixable in the CMS now)** — a wrong date, a missing summary, a
heading level to shift, spacing to correct. Offer to fix these and rerun the
verifier.

**Template issues (a design decision)** — an unbound field, missing table styles,
a card that clips long titles. Describe what is happening and what the choices
are; do not restructure someone's template as part of a content import unless
they ask.

If something cannot be checked — no published item to fetch, no access to the
template — say which check was skipped rather than implying the page was
reviewed.
