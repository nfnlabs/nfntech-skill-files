# Word (.docx) → Webflow CMS import

Word documents lose fidelity in predictable ways: a bolded phrase arrives
as six fragments, a non-breaking space becomes an invisible layout bug, a
section under an unexpected heading level never gets mapped, a rich-text
field silently ends mid-sentence, an image arrives without its alt text.
Eyeballing a few items catches none of it. This companion replaces
eyeballing with a paper trail: every source block is accounted for, every
field is checked before it is written and compared after, and the rendered
page is inspected last.

The live collection schema, and any items already in it, outrank anything
assumed here or in `mapping.json`. Webflow tool shapes: SKILL.md §4.

## Setup

- **Scripts** are in `scripts/` (Python 3.9+, standard library only; no
  `pip install`): `extract_docx.py`, `build_records.py`,
  `validate_records.py`, `verify_items.py`, plus the shared `wfcommon.py`.
  Run them with `python` (`python3` on macOS/Linux), using the path of this
  skill's `scripts/` folder. `python scripts/selftest.py` runs the whole
  pipeline on synthetic documents (exit 0 = healthy); run it first if the
  scripts were moved, edited or run on a new machine.
- **Documents**: ask the user for the path of the .docx files, or use the
  paths they gave. Do not assume a fixed folder.
- **Work directory**: create one per job (e.g. `./wf-import/<date>/` in
  the project, or the session scratch space). Every file below is written
  there and is the audit trail. Mention it in the closing report.
- If neither the scripts nor a shell are available, say so and list what
  the user must run; don't improvise silently.

## Established collection or empty one?

| Signal | Then |
|---|---|
| Collection already has items | Read 2–3 of them (`list_collection_items`, `limit: 3`) **in stage 1** and note their conventions — Option casing, date format, heading depth, summary length, alt-text style. Match them even where a document implies something else. |
| Collection is empty | Choose the mapping shape from `references/mapping-recipes.md` and say which you picked. |
| Existing items disagree with each other | Don't pick one silently. Flag it and ask which convention new items follow. |

## The pipeline

Six gated stages. Run them in order; don't skip a gate because the content
looks simple, and don't read ahead.

### Stage 1 — Discover

1. `list_sites` → site id (skip if given); `get_site` for locales.
2. `get_collection_list` → collection id; `get_collection_details` for the
   target. Save the **raw JSON** to `WORKDIR/schema.json`.
3. Note per field: `slug` (the key you write to), `type`, `isRequired`, and
   for Option fields the exact option strings. List Reference/
   MultiReference fields and the collection each points at.
4. Read 2–3 existing items (see above).
5. Inventory the documents. Every file the person mentioned must appear in
   the plan; if one is missing, say so before starting.
6. Ask only what the documents can't tell you: which collection, one item
   per document or many, publish or leave as drafts, **which locale**, and
   whether dates are D/M or M/D.

### Stage 2 — Extract

```bash
python scripts/extract_docx.py WORKDIR doc1.docx doc2.docx --media
```

Produces `ir.json` (never read it wholesale), `outline.txt` (headings only —
read this to design the mapping) and `extract_report.json`. The report
compares every `<w:t>` node in the document body to what reached the IR,
and also scans **footnotes and endnotes**, whose text is content the IR
does not carry, so it counts as unmatched. **Gate: `unmatched=0`**, or the
remainder is explained and accepted (usually text in a text box, shape or
footnote: ask whether to inline it into the body or drop it). Text in
**headers, footers and comments** is not content; it is listed as
`ignored_parts` and never imported. Nested list items are flattened to one
list level and counted, so check the rendered list. Report
`tracked_deletions_excluded` to the person: that text was deliberately left
out. With `whole_doc` splitting the item title is the **first heading**
(text before it stays in the body); with `table_rows`, map columns with
`{"from": "column", "name": "Header"}`. `--quotes straight|curly` and
`--ellipsis unicode|dots` only if they want typography standardised.

Images missing alt text are counted. Decide with the person: supply alt
text, mark them decorative, or accept empty alt knowingly (see
`accessibility.md`).

### Stage 3 — Map

Write `WORKDIR/mapping.json` from `outline.txt`, using
`references/mapping-recipes.md`. Then:

```bash
python scripts/build_records.py WORKDIR/ir.json WORKDIR/mapping.json WORKDIR
```

**Claiming rules (this settles the old `rest` ambiguity):** `section`,
`keyvalue` and `rest` *claim* the blocks they take; `first_paragraph`
*copies* a paragraph and does **not** claim it, so `rest` still includes it.
Declare specific fields first and `rest` last. Any block no field claims
fails the run: extend the mapping, or exclude it by id with a reason the
person would accept. `--allow-unclaimed` needs explicit agreement, and you
must say what is dropped.

**Dates**: ISO and named-month dates parse. An all-numeric date that could
be D/M or M/D (e.g. `04/05/2025`) **stops the run**; set `"date_format":
"dmy"` or `"mdy"` from the person's answer. Never guess.

Read `coverage.json` warnings: truncations, duplicate slugs that were
suffixed, a plain-text section that swallowed many blocks (a closing
heading is probably missing in the source), required fields absent.

### Stage 4 — Resolve, upload, validate

Before validating:

- **Images**: for each Image/File field and each `<img>` in rich text,
  upload the file from `WORKDIR/media/` with `asset_tool` / `data_assets_tool`
  (read the schema first), then substitute the returned asset URL and the
  alt text into the records. Word's internal media paths never resolve.
- **References**: for each Reference/MultiReference field, list the
  referenced collection (`list_collection_items`, filtered by slug), build
  a slug → item-id map, and replace names/slugs in the records with ids.
  A name with no match is a finding: ask whether to create that item
  first, or leave the field empty. Never invent an id.
- **SEO fields**: if the collection has `seo-title`, `seo-description`,
  `og-image`, derive them only from the document's own text (title,
  summary) — never write new marketing copy. Leave empty if there is
  nothing to derive and say so.

```bash
python scripts/validate_records.py WORKDIR/records.json WORKDIR/schema.json WORKDIR
```

It fails on unknown field slugs, empty required fields, type mismatches,
Option values not in the collection, HTML in a PlainText field, non-ISO
dates, relative links, unresolved references, local/Word image paths, rich
text with tags Webflow strips, and whitespace trapped inside an inline tag.
Trivial issues (trailing/double spaces, Option case) are auto-fixed and
reported. Warnings (table styles, missing alt, `h1` in rich text) don't
block but must be read. **Gate: 0 errors.** Fix the mapping and rerun;
rerunning a script is nearly free.

### Stage 5 — Write (drafts)

Create as **drafts** (`isDraft: true`) always, even if the person wants
them published. Use `create_collection_items` with the `items[]` shape:
each entry carries its own `fieldData`, `isDraft` and `cmsLocaleIds` (or
`allCmsLocales: true`). Omitting locale writes the primary locale only;
pass the right `cmsLocaleIds` (from `get_site`) if the documents belong to
another locale. Batch about 25 entries per action; a request creates at
most 100 locale variants.

Emit the arguments from `records.json` with a script; do not retype prose.
Save every response to `WORKDIR/create_responses.json`: you need the ids.
If a batch fails, don't retry blindly — read the error, check which slugs
landed (`list_collection_items` with a `slug` filter), and resend only the
missing ones. Blind retries create duplicates.

Do **not** include a publish in the same call as the creates.

### Stage 6 — Verify, publish, then look at the page

**6a. Round-trip diff.** Read the items back with `list_collection_items`
(`limit: 100`, loop `offset` until you have all), save the raw responses
to `WORKDIR/items_live.json`, then:

```bash
python scripts/verify_items.py WORKDIR/records.json WORKDIR/items_live.json WORKDIR
```

Per record, per field it checks existence, canonical text equality, length,
the last 40 characters and block count, so a missing paragraph, a mid-field
deletion and a truncated tail are separate findings. Read
`verify_report.md`. Fix with `update_collection_items`, re-read, re-run.
**Gate: `verified N records: N clean, 0 problems`.**

**6b. Publish** only after 6a is clean **and the person asked** in this
conversation, through `publishing-handoff.md`'s gate:
`publish_collection_items` with `items: [{id}]` (and `cmsLocaleIds` where
relevant), in batches. Publishing items does not publish design or template
changes; the site needs publishing separately for those.

**6c. Review the rendered pages** with `references/ui-review.md`: bindings
of every imported field, the rendered markup of one published item, the
collection list. Report two short lists: **content issues** (fixable now:
a date, a missing summary, a heading level) and **template issues** (a
design decision for the user: an unbound field, missing table styles).
Say which checks you skipped.

## Token discipline

- Never read a `.docx`, `ir.json` or `records.json` wholesale. Read
  `outline.txt`, the printed summaries, `coverage.json`, `validation.json`
  and `verify_report.md`.
- Content goes disk → script → tool call. Build request bodies with a
  script; don't retype prose.
- Batch reads; sample one representative item's rich text in full, once,
  at stage 6. The scripts do the exhaustive comparison.

## Closing report

```text
Documents processed: 3 (12 items created, all verified clean)
Coverage:   428/431 blocks used; 3 excluded (cover page, TOC) - listed below
Normalized: 47 non-breaking spaces, 12 double spaces, 9 split bold runs,
            4 spaces before punctuation, 6 Word list prefixes
Images:     5 uploaded; 2 had no alt text - supplied / marked decorative
References: 12 authors resolved by slug; 1 unmatched ("J. Smith") - left empty
Published:  12 items live (on request)
UI review:  headings and body render correctly; the table in "Travel
            Reimbursement" is unstyled - needs a rich-text table style
Needs you:  2 documents had no Summary section, so those cards show no excerpt
```

Keep the work directory in place and mention it: `coverage.json` and
`verify_report.md` are the evidence.
