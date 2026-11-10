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
| `column` | `{"name": "Header"}` | with `table_rows` splitting: the cell under that column header |
| `rest` | – | every block no earlier field **claimed**. Declare it last |
| `const` | `{"const": false}` | a fixed value, e.g. a Switch default |

Add `"required": true` to `section`/`keyvalue` to get a warning when the document
lacks it, instead of a quietly empty field.

## What claims a block

| Source | Claims the blocks it takes? |
|---|---|
| `record_title`, `section`, `keyvalue`, `rest` | **Yes** - later fields can't take them again |
| `first_paragraph` | **No** - it copies, so `rest` still includes that paragraph |
| `slugify`, `const`, `column` | n/a |

Content appears twice only when `first_paragraph` is used. To move text
instead of copying it, use a `section`.

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

An all-numeric date that could be D/M or M/D (`04/05/2025`) **stops the run**; the
builder never guesses. Set top-level `"date_format": "dmy"` or `"mdy"` from the
person's answer. A day above 12 (`04/18/2025`) is unambiguous and parses without it.

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

`excerpt` uses `first_paragraph`, which **copies** without claiming, so `rest` still
includes that paragraph - usually wanted (the excerpt is a preview). To move it
instead, use a `section`.

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
- **Duplicated content** appearing in two fields → either `first_paragraph` (copies by
  design) or a field order problem: declare `section`/`keyvalue` before `rest`.
- **A plain-text section that swallowed many blocks** → the source has no closing
  heading after it; fix the document or map it `richtext`.
