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
| Image / MultiImage / File | an uploaded asset URL or id | Word's internal media paths never resolve — upload first. **Alt text** is a property of the image: carry it from the document (or a paired alt field) and never ship a meaningful image without it. |
| Reference / MultiReference | item id(s) | list the referenced collection, build slug → id, substitute ids. An unmatched name is a finding to report, never a guessed id. Create the referenced item first if asked. |

`name` and `slug` are required on every create. Field keys in `fieldData` are
field **slugs**, not display names — "Post Body" is `post-body`.

## Rich text: what survives

Believed to be reliably supported (**verify against the current Webflow rich-text
docs and by reading one item back**): `p`, `h1`–`h6`, `ul`, `ol`, `li`, `a`, `strong`,
`em`, `u`, `s`, `sup`, `sub`, `blockquote`, `br`, `figure`, `figcaption`, `img`,
`code`, `pre`.

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

- `create_collection_items` writes staged items using the **`items[]`** shape (each
  entry has its own `fieldData`, `isDraft`, `cmsLocaleIds`); the top-level
  `fieldData` array is deprecated. `isDraft: true` keeps the item off the live site;
  `isDraft: false` still requires publishing.
- `publish_collection_items` pushes items live using `items: [{id, cmsLocaleIds?}]`
  (`itemIds` is deprecated). Batch conservatively and only after verification.
- Publishing items does **not** publish design or template changes. If the
  template was edited, the site needs publishing separately.
- `unpublish_collection_items` reverts items to draft, up to 100 per call, and is
  the clean way to undo a premature publish.
- `delete_collection_items` is destructive: treat it as not undoable unless you have
  confirmed otherwise. When a run goes wrong, prefer updating or unpublishing the
  items you created over deleting, and only delete ids you can prove came from this
  run (`create_responses.json`). Export the collection to CSV before any bulk change.

## Localization

If the site has secondary locales, items created without `cmsLocaleIds` (or `allCmsLocales: true`) land
in the primary locale only. Secondary locales stay empty and their pages fall back —
which looks like missing content. Ask which locale the documents are for before
writing, and if it is not the primary one, pass its `cmsLocaleId` (from `get_site`).

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
