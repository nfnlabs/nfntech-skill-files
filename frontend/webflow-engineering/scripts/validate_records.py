#!/usr/bin/env python3
"""Stage 4 - validate: records.json vs the live collection schema.

usage: validate_records.py RECORDS SCHEMA WORKDIR

SCHEMA is the raw JSON saved from data_cms_tool get_collection_details.
Exit 0 = clean, 1 = errors (nothing may be written), warnings never block.
Trivial issues (trailing/double spaces, Option case) are fixed in place.
"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wfcommon import die, load, save  # noqa: E402

OK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "a", "strong", "em", "u", "s",
           "sup", "sub", "blockquote", "br", "figure", "figcaption", "img", "code", "pre", "table",
           "tbody", "thead", "tr", "td", "th"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
OID = re.compile(r"^[0-9a-f]{24}$")


def find_fields(schema):
    for path in (("fields",), ("collection", "fields"), ("data", "fields")):
        cur = schema
        for k in path:
            cur = cur.get(k) if isinstance(cur, dict) else None
        if isinstance(cur, list):
            return cur
    if isinstance(schema, list) and schema and "slug" in schema[0]:
        return schema
    die("could not find a fields list in the schema file")


def option_names(f):
    for src in (f.get("validations") or {}, f.get("metadata") or {}):
        opts = src.get("options")
        if opts:
            return [o.get("name") for o in opts]
    return []


def main():
    if len(sys.argv) != 4:
        die(__doc__)
    records, schema, work = load(sys.argv[1]), load(sys.argv[2]), Path(sys.argv[3])
    fields = {f["slug"]: f for f in find_fields(schema)}
    fields.setdefault("name", {"slug": "name", "type": "PlainText", "isRequired": True})
    fields.setdefault("slug", {"slug": "slug", "type": "PlainText", "isRequired": True})
    errors, warns, fixed = [], [], []

    for n, rec in enumerate(records):
        d, who = rec["fieldData"], "record %d (%s)" % (n, rec.get("doc", ""))
        for slug, v in list(d.items()):
            f = fields.get(slug)
            if f is None:
                errors.append("%s: unknown field slug '%s'" % (who, slug))
                continue
            t = f.get("type")
            if isinstance(v, str):
                nv = re.sub(r" {2,}", " ", v).strip() if t != "RichText" else v.strip()
                if nv != v:
                    d[slug] = v = nv
                    fixed.append("%s.%s: whitespace" % (who, slug))
            if t in ("PlainText", "Email", "Phone", "Option", "Link", "VideoLink", "Color"):
                if isinstance(v, str) and re.search(r"<[a-zA-Z/][^>]*>", v):
                    errors.append("%s.%s: HTML in a %s field (would show as visible tags)" % (who, slug, t))
            if t == "Option" and v is not None:
                names = option_names(f)
                if names and v not in names:
                    ci = [x for x in names if x and x.lower() == str(v).lower()]
                    if ci:
                        d[slug] = ci[0]
                        fixed.append("%s.%s: option case -> %s" % (who, slug, ci[0]))
                    else:
                        errors.append("%s.%s: option '%s' not in %s" % (who, slug, v, names))
            elif t == "DateTime" and v is not None and not ISO.match(str(v)):
                errors.append("%s.%s: date '%s' is not ISO 8601 with Z" % (who, slug, v))
            elif t == "Number" and v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
                errors.append("%s.%s: number must be numeric, got %r" % (who, slug, v))
            elif t == "Switch" and v is not None and not isinstance(v, bool):
                errors.append("%s.%s: switch must be boolean, got %r" % (who, slug, v))
            elif t == "Slug" or slug == "slug":
                if v and not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", str(v)):
                    errors.append("%s.%s: slug '%s' would be rewritten by Webflow" % (who, slug, v))
            elif t in ("Link",) and v and not re.match(r"^(https?://|mailto:|tel:)", str(v)):
                errors.append("%s.%s: link must be absolute (https://, mailto:, tel:)" % (who, slug))
            elif t in ("Reference",) and v and not (isinstance(v, str) and OID.match(v)):
                errors.append("%s.%s: reference must be an item id - resolve '%s' to an id first" % (who, slug, v))
            elif t in ("MultiReference",) and v and not (isinstance(v, list) and all(OID.match(str(x)) for x in v)):
                errors.append("%s.%s: multi-reference must be a list of item ids - resolve by slug first" % (who, slug))
            elif t in ("Image", "File") and v and isinstance(v, str) and (v.startswith("media/") or v.startswith("word/")):
                errors.append("%s.%s: local/Word media path - upload the asset and use its URL" % (who, slug))
            elif t == "RichText" and isinstance(v, str):
                for tag in set(re.findall(r"</?([a-zA-Z0-9]+)", v)):
                    if tag.lower() not in OK_TAGS:
                        errors.append("%s.%s: tag <%s> is stripped by Webflow rich text" % (who, slug, tag))
                if re.search(r"<(strong|em|a|u|s)[^>]*>\s|\s</(strong|em|a|u|s)>", v):
                    errors.append("%s.%s: whitespace trapped inside an inline tag (invisible-gap bug)" % (who, slug))
                for href in re.findall(r'<a[^>]*href="([^"]*)"', v):
                    if href.startswith("#"):
                        warns.append("%s.%s: in-page anchor link '%s' - check it resolves on the page" % (who, slug, href))
                    elif not re.match(r"^(https?://|mailto:|tel:)", href):
                        errors.append("%s.%s: relative or bare link '%s' - use an absolute URL" % (who, slug, href))
                if "<table" in v:
                    warns.append("%s.%s: table - rich text has no table styles; add template styles or use an embed" % (who, slug))
                for m in re.finditer(r"<img\b[^>]*>", v):
                    if not re.search(r'alt="[^"]+"', m.group(0)):
                        warns.append("%s.%s: image has no alt text - add it (accessibility)" % (who, slug))
                    if 'src="media/' in m.group(0) or 'src="media\\' in m.group(0) or "word/" in m.group(0):
                        errors.append("%s.%s: <img> still points at a local/Word path - upload and substitute the URL" % (who, slug))
                if re.search(r"<h1[ >]", v):
                    warns.append("%s.%s: <h1> inside rich text duplicates the page h1 - raise heading_shift" % (who, slug))
        for slug, f in fields.items():
            if f.get("isRequired") and (slug not in d or d[slug] in (None, "", [])):
                errors.append("%s: required field '%s' is empty" % (who, slug))
            if f.get("type") == "Image" and f.get("slug") in d and not any(
                    k.endswith("alt") for k in d):
                warns.append("%s: image field '%s' has no alt-text companion field populated" % (who, slug))

    res = {"records": len(records), "errors": errors, "warnings": warns, "auto_fixed": fixed}
    save(work / "records.json", records)  # includes in-place fixes
    save(work / "validation.json", res)
    print("validated %d records: %d errors, %d warnings, %d auto-fixed" % (len(records), len(errors), len(warns), len(fixed)))
    for e in errors[:40]:
        print("  ERROR:", e)
    for w in warns[:20]:
        print("  warn:", w)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
