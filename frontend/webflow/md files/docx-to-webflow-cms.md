# DOCX → Webflow CMS — Skill Guide

> Internal reference for the docx-to-webflow-cms skill. This combines the main
> skill guide with its three reference documents (mapping recipes, Webflow CMS
> notes, and UI review procedure). The skill also ships four Python scripts
> (`extract_docx.py`, `build_records.py`, `validate_records.py`,
> `verify_items.py`) that this document does not include inline — those are
> code assets, not documentation, and are required to actually run the
> pipeline described below. Ask if you'd like those bundled separately.

---

---
name: docx-to-webflow-cms
description: Import content from Word documents (.docx) into Webflow CMS collections with byte-level fidelity — clean spacing and punctuation, correct rich-text structure, nothing truncated or skipped — then verify every item round-trip and review how the pages actually render. Use this skill whenever a .docx (or several) needs to become CMS items, or someone says "add this doc to Webflow", "populate the CMS from these documents", "bulk upload these Word files to my collection", "migrate this content into Webflow", "fix the spacing/formatting of CMS content that came from Word", or asks to check that an earlier Word-to-Webflow import came through complete and correct. Also use it when the request is a single document into a single collection — the verification pass is the point, not just the writing.
compatibility: Requires the Webflow MCP connector (data_sites_tool, data_cms_tool, data_pages_tool, data_element_tool, asset_tool) and a bash/Python 3 environment for the bundled scripts.
---

# DOCX → Webflow CMS

Word documents lose fidelity in transit in predictable ways: a bolded phrase
arrives as six fragments, a non-breaking space becomes an invisible layout bug,
a section under an unexpected heading level never gets mapped, and a rich-text
field silently ends mid-sentence. Eyeballing a few items does not catch any of
this. This skill replaces eyeballing with a paper trail: every source block is
accounted for, every field is checksummed before it is written and compared
after, and the rendered page is inspected last.

## The pipeline

Six stages, gated. Do not skip a gate because the content looks simple; the
cheap stages are the ones that make the expensive stage trustworthy.

```
1 Discover  → collection schema + document inventory
2 Extract   → docx → ir.json (+ coverage audit)         scripts/extract_docx.py
3 Map       → mapping.json → records.json (+ coverage)  scripts/build_records.py
4 Validate  → records vs live schema                    scripts/validate_records.py
5 Write     → create as drafts, batched                 data_cms_tool
6 Verify    → round-trip diff, then publish, then UI    scripts/verify_items.py
```

Work in one directory (e.g. `/home/claude/wf-import/`). Everything below writes
there, and the files are the audit trail if anything is questioned later.

## Token discipline

Document content is bulky and repetitive; putting it through the context window
twice is the main cost of this task and also the main source of transcription
errors. So:

- **Never read a .docx or `ir.json` or `records.json` wholesale.** The scripts
  read them. Read `outline.txt`, the printed summaries, `coverage.json`,
  `validation.json` and `verify_report.md` — all small and designed to be read.
- Content goes disk → script → tool call. When creating items, build the request
  body with a script that emits the tool arguments, or pass the field data
  through directly; do not retype prose.
- Batch tool calls. `data_cms_tool` takes an `actions` array — put the schema
  read, the item creates and the publish in as few calls as the API allows
  (create in batches of ~25 items per action, several actions per call).
- Inspect one representative item's rich text in full, once, at stage 6. Sample,
  don't sweep — the scripts do the exhaustive comparison.
- If a stage fails, fix `mapping.json` and rerun the script. Rerunning a script
  is nearly free; re-deriving content by hand is not.

## Stage 1 — Discover

Read the target before shaping the content to it.

1. `data_sites_tool` → `list_sites` for the site ID (skip if given).
2. `data_cms_tool` → `get_collection_list` for the collection ID.
3. `data_cms_tool` → `get_collection_details` for the target collection. Save
   the raw JSON response to `WORKDIR/schema.json` — stage 4 reads it.
4. Note for each field: `slug` (the key you write to, not the display name),
   `type`, `isRequired`, and for Option fields the exact option strings.
5. Inventory the documents: `ls /mnt/user-data/uploads`. Every file the person
   mentioned must appear in the plan; if one is missing, say so before starting.

Ask the person only what the documents cannot tell you — usually just: which
collection, whether each document is one item or many, and whether to publish or
leave as drafts. Everything else comes from the outline in stage 2.

## Stage 2 — Extract

```bash
python3 scripts/extract_docx.py WORKDIR /mnt/user-data/uploads/*.docx --media
```

Produces `ir.json` (block-level intermediate representation), `outline.txt`
(headings only — read this to design the mapping) and `extract_report.json`.

The report includes a coverage audit: every `w:t` node in the document is counted
and compared against what reached the IR. `unmatched=0` means nothing was
dropped. If it is non-zero, open `extract_report.json`, look at
`unmatched_fragments`, and resolve before continuing — usually text inside a
shape, a text box, a footnote or a tracked deletion. Report
`tracked_deletions_excluded` to the person if non-zero: deleted text is
excluded by design, and they should know it was there.

Flags: `--quotes straight|curly` and `--ellipsis unicode|dots` only if the person
wants typography standardized; the default preserves what the author wrote.

## Stage 3 — Map

Write `WORKDIR/mapping.json` from `outline.txt`. The full field-source reference
and worked examples for the common document shapes are in
`references/mapping-recipes.md` — read it before writing your first mapping.

```json
{
  "split": {"mode": "heading", "level": 2},
  "heading_shift": 1,
  "exclude_blocks": {"handbook.docx": [0, 1]},
  "exclude_reason": "document title and TOC line, not record content",
  "fields": {
    "name":     {"from": "record_title"},
    "slug":     {"from": "slugify", "source": "name"},
    "author":   {"from": "keyvalue", "key": "Author", "as": "plain"},
    "published":{"from": "keyvalue", "key": "Date", "as": "date"},
    "summary":  {"from": "section", "match": "Summary", "as": "plain", "maxlen": 300},
    "body":     {"from": "rest", "as": "richtext"}
  }
}
```

Two things that bite: field keys are collection field **slugs**, and `rest` only
picks up blocks no earlier field claimed — so declare specific fields before the
catch-all. Set `heading_shift` so document headings land below the page's `h1`
(a document `h2` becoming an `h3` inside rich text is the usual answer).

```bash
python3 scripts/build_records.py WORKDIR/ir.json WORKDIR/mapping.json WORKDIR
```

**This is the gate against missed content.** Every non-excluded block must be
claimed by a field. Unclaimed blocks fail the run and are printed with previews.
Two legitimate responses: extend the mapping to cover them, or add their ids to
`exclude_blocks` with a reason the person would accept. `--allow-unclaimed`
exists but requires explicit agreement — and say what is being dropped.

Also read the `warnings` in `coverage.json`: ambiguous dates, truncations against
a `maxlen`, duplicate slugs that were suffixed.

## Stage 4 — Validate

```bash
python3 scripts/validate_records.py WORKDIR/records.json WORKDIR/schema.json WORKDIR
```

Fails on: unknown field slugs, empty required fields, type mismatches, Option
values not in the collection, HTML in a PlainText field, non-ISO dates,
unusable URLs, rich text with tags Webflow strips, and whitespace trapped inside
an inline tag (the invisible-gap bug). Trivial issues — trailing spaces, double
spaces, Option case mismatches — are auto-fixed in place and reported.

Fix and rerun until it passes. Creating items you already know are wrong turns a
five-minute mapping fix into a cleanup job.

## Stage 5 — Write

Create as **drafts** first (`isDraft: true`), always, even when the person wants
them published. A draft that is wrong is a private problem; a published one is a
public one.

Use `data_cms_tool` → `create_collection_items`, whose `fieldData` is an array,
so many items go in one action. Batch ~25 per action and keep each request under
a few hundred KB. Emit the arguments from `records.json` with a script rather
than retyping prose.

Save every response to `WORKDIR/create_responses.json` — you need the returned
item ids. If a batch fails, do not retry blindly: read the error, check whether
part of the batch landed (`list_collection_items` filtered by slug), and only
then resend the missing ones. Duplicate items are the usual cost of a blind
retry.

If the collection has Image/File fields, images extracted to `WORKDIR/media/`
must be uploaded first via `asset_tool` (or `data_assets_tool`) and the returned
asset URLs substituted into the records before writing. Rich-text `<img src>`
values from the IR point at Word's internal media paths and will not resolve
until they are replaced.

## Stage 6 — Verify, publish, then look at the page

This stage is not optional and not a formality.

**6a. Round-trip diff.** Read the items back with `list_collection_items`
(paginate: `limit` 100 plus `offset` until you have them all), save the raw
responses to `WORKDIR/items_live.json`, then:

```bash
python3 scripts/verify_items.py WORKDIR/records.json WORKDIR/items_live.json WORKDIR
```

Per record, per field it checks existence, canonical text equality, character
count, the final 40 characters, and block count — so a missing paragraph, a
mid-field deletion and a truncated tail each surface as a distinct finding. Read
`verify_report.md`. Resolve every problem before publishing: fix the record and
`update_collection_items`, then rerun the verifier. `verified N records: N clean,
0 problems` is the bar.

**6b. Publish** only after 6a is clean and the person asked for it:
`publish_collection_items` with the item ids (batches of 100). Publishing an item
does not publish site-wide design changes; say so rather than letting them
wonder why the template still looks old.

**6c. Review the rendered pages.** Data being correct in the CMS is not the same
as the page looking right — an `h4` inside rich text with no style bound, a
table with no styling, a summary overflowing its card. Follow
`references/ui-review.md`: it covers checking the collection template's bindings
with `data_pages_tool` / `data_element_tool`, fetching a published item URL to
confirm the markup arrived, and what to look for on the collection list page.
Report findings as a short list of what looks right and what needs a design
change, separating "content problem I can fix" from "template problem you need
to decide about".

## Closing report

End with a compact summary the person can act on, not a narration of the run:

```
Documents processed: 3 (12 items created, all verified clean)
Coverage:   428/431 blocks used; 3 excluded (cover page, TOC) — listed below
Normalized: 47 non-breaking spaces, 12 double spaces, 9 split bold runs,
            4 spaces before punctuation, 6 Word list prefixes
Published:  12 items live
UI review:  headings and body render correctly; the table in "Travel
            Reimbursement" is unstyled — needs a rich-text table style
Needs you:  2 documents had no Summary section, so those cards show no excerpt
```

Keep the workspace directory in place and mention it — `coverage.json` and
`verify_report.md` are the evidence if anyone asks whether something was missed.

## Reference files

- `references/mapping-recipes.md` — every field source and `as` type, plus
  worked mappings for the four common document shapes. Read before stage 3.
- `references/webflow-cms-notes.md` — field types, rich-text tag support, limits,
  draft/publish and locale behaviour, and the API gotchas that cause silent
  content loss. Read before stages 4–5.
- `references/ui-review.md` — the stage 6c procedure. Read before reviewing.


---

# Reference: Mapping Recipes

# mapping.json reference and recipes

Contents: [split modes](#split-modes) · [field sources](#field-sources) ·
[`as` types](#as-types) · [recipes](#recipes) · [debugging unclaimed blocks](#debugging-unclaimed-blocks)

## split modes

| mode | meaning | when |
|---|---|---|
| `{"mode": "heading", "level": N}` | one record per heading at level ≤ N | a document containing many entries |
| `{"mode": "whole_doc"}` | one record per file; first heading becomes the title | one document = one CMS item |
| `{"mode": "table_rows", ...}` | one record per table row | data tables; map columns by header name |

With `heading`, blocks appearing *before* the first record heading (cover page,
intro, TOC) trigger a warning and stay unclaimed. Either lower the level, or
exclude them by id with a reason.

## field sources

Keys in `fields` are the collection's **field slugs** (from
`get_collection_details`), not display names. `name` and `slug` are always
required by Webflow.

| `from` | takes | notes |
|---|---|---|
| `record_title` | the record's own heading text | plain text, punctuation-normalized |
| `slugify` | `{"source": "name"}` | ASCII, lowercase, hyphenated, deduped automatically |
| `section` | `{"match": "Summary"}` | heading whose text starts with `match` (case-insensitive, trailing colon ignored); takes the blocks beneath it, not the heading |
| `keyvalue` | `{"key": "Author"}` | a paragraph shaped `Author: Priya Nair` anywhere in the record |
| `first_paragraph` | – | the first real paragraph; good for auto-excerpts with `maxlen` |
| `rest` | – | every block no earlier field claimed. Declare it last |
| `const` | `{"const": false}` | a fixed value, e.g. a Switch default |

Add `"required": true` to `section`/`keyvalue` to get a warning when the document
lacks it, instead of a quietly empty field.

## `as` types

| `as` | output | for Webflow field type |
|---|---|---|
| `richtext` | structured HTML — headings, lists, blockquotes, tables, figures | RichText |
| `plain` | tag-free single-spaced text | PlainText, Email, Phone, Option |
| `date` | ISO 8601 `…T00:00:00.000Z` | DateTime |
| `number` | int or float | Number |
| `switch` | boolean from yes/true/y/1/on | Switch |
| `list` | array split on `,` `;` newline | MultiReference staging, or joined text |

`maxlen` truncates at a word boundary with an ellipsis and logs a warning — use
it for excerpt fields with a design limit, never on the main body.

Dates written `04/18/2025` are ambiguous. The builder reads them as D/M/Y and
warns. If the documents are American, fix the source or convert before importing
— do not let the warning pass unread.

## recipes

### 1. One long document, many entries under `Heading 2`

```json
{
  "split": {"mode": "heading", "level": 2},
  "heading_shift": 1,
  "exclude_blocks": {"handbook.docx": [0, 1]},
  "exclude_reason": "document title and contents line",
  "fields": {
    "name": {"from": "record_title"},
    "slug": {"from": "slugify", "source": "name"},
    "summary": {"from": "section", "match": "Summary", "as": "plain", "maxlen": 300},
    "body": {"from": "rest", "as": "richtext"}
  }
}
```

### 2. One file per item, metadata in a front block

```json
{
  "split": {"mode": "whole_doc"},
  "heading_shift": 1,
  "fields": {
    "name": {"from": "record_title"},
    "slug": {"from": "slugify", "source": "name"},
    "author": {"from": "keyvalue", "key": "Author", "as": "plain", "required": true},
    "published": {"from": "keyvalue", "key": "Date", "as": "date", "required": true},
    "category": {"from": "keyvalue", "key": "Category", "as": "plain"},
    "excerpt": {"from": "first_paragraph", "as": "plain", "maxlen": 160},
    "post-body": {"from": "rest", "as": "richtext"},
    "featured": {"const": false}
  }
}
```

`excerpt` reuses the first paragraph, which `rest` then also includes — that is
usually wanted (the excerpt is a preview, not a move). If it should be moved
instead, use a `section` for it or accept the duplication knowingly.

### 3. Structured records where each field is its own section

```json
{
  "split": {"mode": "heading", "level": 2},
  "heading_shift": 2,
  "fields": {
    "name": {"from": "record_title"},
    "slug": {"from": "slugify", "source": "name"},
    "role": {"from": "section", "match": "Role", "as": "plain", "required": true},
    "bio": {"from": "section", "match": "Biography", "as": "richtext", "required": true},
    "linkedin": {"from": "keyvalue", "key": "LinkedIn", "as": "plain"},
    "notes": {"from": "rest", "as": "richtext"}
  }
}
```

Keep a `rest` field even when every field is explicitly mapped — it is what turns
"a section nobody mapped" from silent loss into visible content you can then
place properly.

### 4. Updating existing items instead of creating

Build records the same way, then match live items by slug
(`list_collection_items` with a slug filter) and call `update_collection_items`
with `{id, fieldData}`. Slugs are the join key, so do not regenerate them from a
retitled heading — that creates a second item and orphans the first, breaking any
link that pointed at the old URL.

## debugging unclaimed blocks

`build_records.py` prints each unclaimed block as `[id] type: preview`.

- **A heading you did not map** → add a `section`, or make sure a `rest` field
  exists to absorb it.
- **Blocks before the first record** → cover page or TOC; exclude with a reason.
- **A whole tail section** (appendix, contact block) → decide explicitly: map it
  to a field, or exclude it and say so in the closing report.
- **Duplicated content** appearing in two fields → an earlier field claimed it
  and `rest` re-emitted it: check field order, specific before catch-all.


---

# Reference: Webflow CMS Notes

# Webflow CMS notes for content imports

Read before validating and writing. These are the behaviours that cause content
to arrive subtly wrong rather than loudly failing.

## Field types and what they accept

| Type | Write as | Watch for |
|---|---|---|
| PlainText | string | HTML is stored literally and shown as visible tags on the page |
| RichText | HTML string | see the tag table below |
| Slug | lowercase `a-z0-9-` | Webflow silently rewrites anything else, so your saved slug no longer matches and round-trip matching fails |
| DateTime | `2025-04-18T00:00:00.000Z` | a bare `2025-04-18` may be rejected or shifted by timezone |
| Number | number, not string | `"12"` fails validation |
| Switch | boolean | `"yes"` fails |
| Option | the exact option string | case and trailing spaces matter; unknown values are rejected |
| Link / Email / Phone | absolute URL / `mailto:` / `tel:` | a bare `example.com` renders as a broken relative link |
| Image / File | an uploaded asset URL or id | Word's internal media paths never resolve — upload first |
| Reference / MultiReference | item id(s) | resolve by looking up the referenced collection's slugs first |

`name` and `slug` are required on every create. Field keys in `fieldData` are
field **slugs**, not display names — "Post Body" is `post-body`.

## Rich text: what survives

Reliably supported: `p`, `h1`–`h6`, `ul`, `ol`, `li`, `a`, `strong`, `em`, `u`,
`s`, `sup`, `sub`, `blockquote`, `br`, `figure`, `figcaption`, `img`, `code`,
`pre`.

Anything else — `div`, `span`, `style`, `class`, `font`, `table` styling — is
either stripped or arrives unstyled. Notable cases:

- **Tables** keep their markup but Webflow's rich text has no table styles, so
  they render as unstyled rows. Either the template adds styles for
  `table/tr/td` inside the rich-text block, or the content belongs in an HTML
  embed instead. The validator warns whenever a table is present.
- **Inline styles and classes** are dropped. Colour, font and alignment applied
  in Word do not transfer; if the person expects them to, say so early.
- **Whitespace inside inline tags** (`<strong> word </strong>`) renders as a
  visible gap or a missing space depending on the browser. The extractor moves
  those spaces outside the tags; the validator fails if any survive.
- **Heading levels** are not adjusted for you. A document `h1` inside rich text
  gives the page two `h1`s, which is both an accessibility problem and usually a
  visual one. That is what `heading_shift` is for.
- **Empty paragraphs** used as spacers in Word are dropped deliberately —
  Webflow's rich text applies its own block spacing, and empty `<p>` tags
  produce uneven gaps.

## Drafts, publishing and staging

- `create_collection_items` writes to staging. `isDraft: true` keeps the item out
  of the live site entirely; `isDraft: false` still requires publishing.
- `publish_collection_items` pushes items live — up to 100 ids per call.
- Publishing items does **not** publish design or template changes. If the
  template was edited, the site needs publishing separately.
- `unpublish_collection_items` reverts items to draft, up to 100 per call, and is
  the clean way to undo a premature publish.
- Deleting is not undoable through the API. When a run goes wrong, prefer
  updating the items you created over deleting and starting again — and only
  delete ids you can prove came from this run (`create_responses.json`).

## Localization

If the site has secondary locales, items created without `cmsLocaleIds` land in
the primary locale only. Secondary locales stay empty and their pages fall back —
which looks like missing content. Ask which locale the documents are for before
writing, and if it is not the primary one, pass the locale id.

## Rate and size limits

- Batch item creation, but keep batches around 25 items; very large rich-text
  payloads in one request are the usual cause of an opaque failure.
- On a `429` or a timeout, wait and retry the batch — but check first whether it
  partially landed (`list_collection_items` filtered by the slugs in that batch).
  Blind retries create duplicates, and duplicates are worse than a failed batch.
- Paginate reads: `limit` maxes at 100, so loop with `offset` until you have
  every item, or verification will report items as missing that exist.

## Things that look like bugs but are not

- **The slug changed on save.** Webflow normalized it, or it collided with an
  existing item and got a numeric suffix. Match on the returned slug from then on.
- **Text differs but lengths match.** Almost always a character substitution —
  a curly quote, an en dash, a `&amp;`. Compare the canonical forms rather than
  the raw strings, which is what the verifier does.
- **Rich text comes back reordered or re-encoded.** Webflow re-serializes HTML;
  attribute order and entity form are not preserved. Only text-level differences
  are real.


---

# Reference: UI Review Procedure

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

