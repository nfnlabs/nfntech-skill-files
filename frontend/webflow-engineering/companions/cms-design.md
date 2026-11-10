# CMS collection design

Read the live collections first (`get_collection_list`, then
`get_collection_details` for each one you will touch). The existing schema
outranks anything here. Field-type and rich-text behaviour is in
`references/webflow-cms-notes.md`.

## Limits to check before designing

Plan limits change; read the site's plan and current Webflow documentation
instead of quoting numbers from memory. Check at least: items per
collection, fields per collection, collections per site, and CMS API rate
limits. Design so a limit is a decision, not a surprise: a site that will
exceed the item cap needs a different structure, not a workaround.
Reads page at 100 items (`limit` ≤ 100, loop with `offset`).

## Designing a collection

- One collection per **kind of thing** (Posts, Authors, Categories,
  Services). If two collections share most fields, merge them with a
  `type` Option field.
- `name` and `slug` always exist. Pick a slug rule up front (lowercase,
  hyphens, no dates in the slug unless the URL should change).
- Field slugs are stable keys: lowercase, hyphenated, named by meaning
  (`author`, `post-body`), not by presentation. API writes use the slug,
  not the display name.
- Choose the narrowest field type: Option for a closed set, Switch for
  yes/no, Number for numbers, DateTime for dates, Link/Email/Phone for
  those, Image/MultiImage/File for assets, RichText only for body content.
- **References**: use a Reference for "one of" (Post → Author) and a
  MultiReference for "many of" (Post → Categories). Create the referenced
  collection first. A reference needs the referenced item ids, so resolve
  them by slug from the other collection before writing.
- Mark a field **required** only if the template breaks without it.
- Add **help text** to every field an editor will touch.
- Use field groups to keep the editor screen readable.

## Templates and display

- Every field the template shows is bound to an element; every bound
  field exists. Writing a field no element displays hides content.
- Plan empty states: a missing optional image or summary collapses a card.
  Use conditional visibility, not placeholder text.
- Sort order: give lists a real sort field (date, order number) rather
  than relying on creation order.
- Heading level in rich text sits below the page `h1`.

## SEO and accessibility fields (include by default)

- `seo-title` and `seo-description` (PlainText, with help text on length),
  an `og-image`, and where relevant a canonical override.
- Every Image field is paired with an **alt** PlainText field; the
  template binds it to the image's alt. Alt text is content, not an
  afterthought (see `accessibility.md`).

## Changing a live schema

Adding a field is safe. Renaming a slug, changing a type, deleting a field
or deleting a collection can break templates, references and links. Before
any of those: confirm with the user, export the collection (CSV), list the
pages and elements that use it, and prefer adding the new field and
migrating over replacing in place. Deleting is destructive; do it last and
only for ids you can prove.

## Output

Describe the schema as a table (collection, field, slug, type, required,
reference target), say what you changed vs left, and list the template
bindings the user must make in the Designer.
