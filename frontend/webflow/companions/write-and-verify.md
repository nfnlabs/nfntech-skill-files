# Stage 5 — Write

Create as **drafts** first (`isDraft: true`), always, even when the
person wants them published. A draft that is wrong is a private problem;
a published one is a public one.

Use `data_cms_tool` → `create_collection_items`, whose `fieldData` is an
array, so many items go in one action. Batch ~25 per action and keep each
request under a few hundred KB. Emit the arguments from `records.json`
with a script rather than retyping prose.

Save every response to `WORKDIR/create_responses.json` — you need the
returned item ids. If a batch fails, do not retry blindly: read the
error, check whether part of the batch landed (`list_collection_items`
filtered by slug), and only then resend the missing ones. Duplicate items
are the usual cost of a blind retry.

If the collection has Image/File fields, images extracted to
`WORKDIR/media/` must be uploaded first via `asset_tool` (or
`data_assets_tool`) and the returned asset URLs substituted into the
records before writing. Rich-text `<img src>` values from the IR point at
Word's internal media paths and will not resolve until they are replaced.

# Stage 6 — Verify, publish, then look at the page

This stage is not optional and not a formality.

**6a. Round-trip diff.** Read the items back with
`list_collection_items` (paginate: `limit` 100 plus `offset` until you
have them all), save the raw responses to `WORKDIR/items_live.json`, then:

```bash
python3 scripts/verify_items.py WORKDIR/records.json WORKDIR/items_live.json WORKDIR
```

Per record, per field it checks existence, canonical text equality,
character count, the final 40 characters, and block count — so a missing
paragraph, a mid-field deletion and a truncated tail each surface as a
distinct finding. Read `verify_report.md`. Resolve every problem before
publishing: fix the record and `update_collection_items`, then rerun the
verifier. `verified N records: N clean, 0 problems` is the bar.

**6b. Publish** only after 6a is clean and the person asked for it:
`publish_collection_items` with the item ids (batches of 100). Publishing
an item does not publish site-wide design changes; say so rather than
letting them wonder why the template still looks old.

**6c. Review the rendered pages.** Data being correct in the CMS is not
the same as the page looking right — an `h4` inside rich text with no
style bound, a table with no styling, a summary overflowing its card.
Follow `references/ui-review.md`: it covers checking the collection
template's bindings with `data_pages_tool` / `data_element_tool`,
fetching a published item URL to confirm the markup arrived, and what to
look for on the collection list page. Report findings as a short list of
what looks right and what needs a design change, separating "content
problem I can fix" from "template problem you need to decide about".

**Gate:** don't publish until 6a reads `0 problems`. Don't call the job
done until 6c has been walked, even briefly.
