---
name: docx-to-webflow-cms
description: Import content from Word documents (.docx) into Webflow CMS collections with byte-level fidelity — clean spacing and punctuation, correct rich-text structure, nothing truncated or skipped — then verify every item round-trip and review how the pages actually render. Use this skill whenever a .docx (or several) needs to become CMS items, or someone says "add this doc to Webflow", "populate the CMS from these documents", "bulk upload these Word files to my collection", "migrate this content into Webflow", "fix the spacing/formatting of CMS content that came from Word", or asks to check that an earlier Word-to-Webflow import came through complete and correct. Also use it when the request is a single document into a single collection — the verification pass is the point, not just the writing.
compatibility: Requires the Webflow MCP connector (data_sites_tool, data_cms_tool, data_pages_tool, data_element_tool, asset_tool) and a bash/Python 3 environment for the bundled scripts.
---

# DOCX → Webflow CMS

Word documents lose fidelity in transit in predictable ways: a bolded
phrase arrives as six fragments, a non-breaking space becomes an
invisible layout bug, a section under an unexpected heading level never
gets mapped, and a rich-text field silently ends mid-sentence. Eyeballing
a few items does not catch any of this. This skill replaces eyeballing
with a paper trail: every source block is accounted for, every field is
checksummed before it is written and compared after, and the rendered
page is inspected last.

The live collection schema, and any items already in it, outrank
anything assumed in this skill or written in `mapping.json` — Stage 1
reads them before anything is designed against them.

## Before you start

```
ls /mnt/user-data/uploads/*.docx           # documents actually present
```

Note whether the target collection already has items or is empty — it
changes Stage 1 (see below) — and whether the person said publish or
draft. Everything else comes from the schema and the outline, not from
asking.

## Established collection or empty one?

| Signal | Then |
|---|---|
| Collection already has items | Read 2-3 of them (`list_collection_items`) before writing `mapping.json`. Match their established conventions — Option casing, date format, heading depth, how many paragraphs a summary runs — even where a document implies something else. |
| Collection is empty | You choose the mapping shape — follow `references/mapping-recipes.md` defaults and say which you picked. |
| Existing items look inconsistent with each other | Don't silently pick one as "correct." Flag the inconsistency and ask which convention new items should follow. |

Skipping this is the usual cause of a technically-valid import that
still looks wrong next to what's already on the page — right schema,
wrong house style.

## The pipeline

Six stages, gated. Open one companion per stage. Unlike a router that
picks one lane, every stage normally runs for a single import job — the
split across three companions is for token cost, not alternative paths.
Don't read ahead into a later stage's companion before the current gate
passes, and do not skip a gate because the content looks simple; the
cheap stages are the ones that make the expensive stage trustworthy.

| Stage | Does | Open |
|---|---|---|
| 1 Discover | Collection schema + document inventory | `companions/discover-and-extract.md` |
| 2 Extract | docx → `ir.json` (+ coverage audit) | `companions/discover-and-extract.md` |
| 3 Map | `mapping.json` → `records.json` (+ coverage) | `companions/map-and-validate.md` |
| 4 Validate | records vs live schema | `companions/map-and-validate.md` |
| 5 Write | Create as drafts, batched | `companions/write-and-verify.md` |
| 6 Verify | Round-trip diff, then publish, then UI | `companions/write-and-verify.md` |

Stages pair naturally — discovering the schema and extracting the
document are one sitting; mapping and validating iterate together; and
writing is meaningless without the verify pass that follows it. That's
why there are three companions, not six.

Work in one directory (e.g. `/home/claude/wf-import/`). Everything writes
there, and the files are the audit trail if anything is questioned later.

## Token discipline

Document content is bulky and repetitive; putting it through the context
window twice is the main cost of this task and also the main source of
transcription errors. So:

- **Never read a `.docx` or `ir.json` or `records.json` wholesale.** The
  scripts read them. Read `outline.txt`, the printed summaries,
  `coverage.json`, `validation.json` and `verify_report.md` — all small
  and designed to be read.
- Content goes disk → script → tool call. When creating items, build the
  request body with a script that emits the tool arguments, or pass the
  field data through directly; do not retype prose.
- Batch tool calls. `data_cms_tool` takes an `actions` array — put the
  schema read, the item creates and the publish in as few calls as the
  API allows (create in batches of ~25 items per action, several actions
  per call).
- Inspect one representative item's rich text in full, once, at stage 6.
  Sample, don't sweep — the scripts do the exhaustive comparison.
- If a stage fails, fix `mapping.json` and rerun the script. Rerunning a
  script is nearly free; re-deriving content by hand is not.

## Closing report

End with a compact summary the person can act on, not a narration of the
run:

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

Keep the workspace directory in place and mention it — `coverage.json`
and `verify_report.md` are the evidence if anyone asks whether something
was missed.

## Reference files (unchanged, read at the stage that needs them)

- `references/mapping-recipes.md` — every field source and `as` type,
  plus worked mappings for the four common document shapes. Read before
  stage 3.
- `references/webflow-cms-notes.md` — field types, rich-text tag support,
  limits, draft/publish and locale behaviour, and the API gotchas that
  cause silent content loss. Read before stages 4–5.
- `references/ui-review.md` — the stage 6c procedure. Read before
  reviewing.
