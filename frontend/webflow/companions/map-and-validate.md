# Stage 3 — Map

Write `WORKDIR/mapping.json` from `outline.txt`. The full field-source
reference and worked examples for the common document shapes are in
`references/mapping-recipes.md` — read it before writing your first
mapping.

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

Two things that bite: field keys are collection field **slugs**, and
`rest` only picks up blocks no earlier field claimed — so declare
specific fields before the catch-all. Set `heading_shift` so document
headings land below the page's `h1` (a document `h2` becoming an `h3`
inside rich text is the usual answer).

```bash
python3 scripts/build_records.py WORKDIR/ir.json WORKDIR/mapping.json WORKDIR
```

**This is the gate against missed content.** Every non-excluded block
must be claimed by a field. Unclaimed blocks fail the run and are printed
with previews. Two legitimate responses: extend the mapping to cover
them, or add their ids to `exclude_blocks` with a reason the person would
accept. `--allow-unclaimed` exists but requires explicit agreement — and
say what is being dropped.

Also read the `warnings` in `coverage.json`: ambiguous dates, truncations
against a `maxlen`, duplicate slugs that were suffixed.

# Stage 4 — Validate

```bash
python3 scripts/validate_records.py WORKDIR/records.json WORKDIR/schema.json WORKDIR
```

Fails on: unknown field slugs, empty required fields, type mismatches,
Option values not in the collection, HTML in a PlainText field, non-ISO
dates, unusable URLs, rich text with tags Webflow strips, and whitespace
trapped inside an inline tag (the invisible-gap bug). Trivial issues —
trailing spaces, double spaces, Option case mismatches — are auto-fixed
in place and reported.

Fix and rerun until it passes. Creating items you already know are wrong
turns a five-minute mapping fix into a cleanup job.

**Gate:** don't move to write until validation passes clean.
