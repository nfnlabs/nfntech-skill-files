# Stage 1 — Discover

Read the target before shaping the content to it.

1. `data_sites_tool` → `list_sites` for the site ID (skip if given).
2. `data_cms_tool` → `get_collection_list` for the collection ID.
3. `data_cms_tool` → `get_collection_details` for the target collection.
   Save the raw JSON response to `WORKDIR/schema.json` — stage 4 reads it.
4. Note for each field: `slug` (the key you write to, not the display
   name), `type`, `isRequired`, and for Option fields the exact option
   strings.
5. Inventory the documents: `ls /mnt/user-data/uploads`. Every file the
   person mentioned must appear in the plan; if one is missing, say so
   before starting.

Ask the person only what the documents cannot tell you — usually just:
which collection, whether each document is one item or many, and whether
to publish or leave as drafts. Everything else comes from the outline in
stage 2.

# Stage 2 — Extract

```bash
python3 scripts/extract_docx.py WORKDIR /mnt/user-data/uploads/*.docx --media
```

Produces `ir.json` (block-level intermediate representation),
`outline.txt` (headings only — read this to design the mapping) and
`extract_report.json`.

The report includes a coverage audit: every `w:t` node in the document is
counted and compared against what reached the IR. `unmatched=0` means
nothing was dropped. If it is non-zero, open `extract_report.json`, look
at `unmatched_fragments`, and resolve before continuing — usually text
inside a shape, a text box, a footnote or a tracked deletion. Report
`tracked_deletions_excluded` to the person if non-zero: deleted text is
excluded by design, and they should know it was there.

Flags: `--quotes straight|curly` and `--ellipsis unicode|dots` only if the
person wants typography standardized; the default preserves what the
author wrote.

**Gate:** don't move to mapping until `unmatched=0` or the non-zero
remainder is explained and accepted.
