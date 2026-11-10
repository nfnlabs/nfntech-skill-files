#!/usr/bin/env python3
"""Stage 3 - map: ir.json + mapping.json -> records.json + coverage.json.

usage: build_records.py IR MAPPING WORKDIR [--allow-unclaimed]

Claiming rules (this resolves "does rest repeat content?"):
  * section, keyvalue, rest      CLAIM the blocks they take.
  * record_title                 claims the record heading.
  * first_paragraph              COPIES a paragraph and does not claim it, so
                                 `rest` still includes it. Use `section` if the
                                 text should move instead of being duplicated.
  * rest takes every non-excluded block no earlier field claimed. Declare last.
Any block that nothing claims fails the run (unless --allow-unclaimed).
"""
import html
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wfcommon import clean_text, die, load, save, slugify  # noqa: E402

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def shift_heading(b, n):
    lvl = min(6, b["level"] + n)
    return "<h%d>%s</h%d>" % (lvl, b["html"], lvl)


def block_html(b, shift):
    t = b["type"]
    if t == "heading":
        return shift_heading(b, shift)
    if t == "paragraph":
        return "<p>%s</p>" % b["html"]
    if t == "image":
        src = b.get("src") or ""
        return '<figure><img src="%s" alt="%s"></figure>' % (html.escape(src), html.escape(b.get("alt", ""), quote=True))
    if t == "table":
        rows = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in b["rows"])
        return "<table>%s</table>" % rows
    return ""


def render_blocks(blocks, shift):
    out, i = [], 0
    while i < len(blocks):
        b = blocks[i]
        if b["type"] == "list_item":
            tag = "ol" if b.get("ordered") else "ul"
            items = []
            while i < len(blocks) and blocks[i]["type"] == "list_item" and \
                    (blocks[i].get("ordered") == b.get("ordered")):
                items.append("<li>%s</li>" % blocks[i]["html"])
                i += 1
            out.append("<%s>%s</%s>" % (tag, "".join(items), tag))
            continue
        out.append(block_html(b, shift))
        i += 1
    return "".join(out)


def plain_of(blocks):
    return clean_text(" ".join(b.get("text", "") for b in blocks if b["type"] != "image"))


def parse_date(s, fmt, warnings, ctx):
    s = clean_text(s)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", s)
        if m:
            a, b, y = map(int, m.groups())
            if a > 12:
                d, mo = a, b
            elif b > 12:
                mo, d = a, b
            elif a == b:
                d, mo = a, b
            elif fmt == "dmy":
                d, mo = a, b
            elif fmt == "mdy":
                mo, d = a, b
            else:
                die("AMBIGUOUS DATE '%s' (%s): could be D/M or M/D. Set \"date_format\": \"dmy\" or \"mdy\" "
                    "in mapping.json, or fix the source. Not guessing." % (s, ctx))
        else:
            m = re.match(r"^([A-Za-z]{3,9})\.? (\d{1,2}),? (\d{4})$", s) or None
            if m and m.group(1)[:3].lower() in MONTHS:
                mo, d, y = MONTHS[m.group(1)[:3].lower()], int(m.group(2)), int(m.group(3))
            else:
                m = re.match(r"^(\d{1,2}) ([A-Za-z]{3,9}),? (\d{4})$", s)
                if m and m.group(2)[:3].lower() in MONTHS:
                    d, mo, y = int(m.group(1)), MONTHS[m.group(2)[:3].lower()], int(m.group(3))
                else:
                    warnings.append("unparseable date '%s' (%s)" % (s, ctx))
                    return None
    try:
        return datetime(y, mo, d).strftime("%Y-%m-%dT00:00:00.000Z")
    except ValueError:
        warnings.append("invalid date '%s' (%s)" % (s, ctx))
        return None


def truncate(s, n, warnings, ctx):
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(",;:.") + "…"
    warnings.append("truncated to %d chars (%s)" % (n, ctx))
    return cut


def split_records(blocks, split, excluded):
    live = [b for b in blocks if b["id"] not in excluded]
    mode = split.get("mode", "whole_doc")
    if mode == "whole_doc":
        return [live], []
    if mode == "heading":
        lvl = split.get("level", 2)
        recs, cur, pre = [], None, []
        for b in live:
            if b["type"] == "heading" and b["level"] <= lvl:
                cur = [b]
                recs.append(cur)
            elif cur is None:
                pre.append(b)
            else:
                cur.append(b)
        return recs, pre
    if mode == "table_rows":
        recs = []
        for b in live:
            if b["type"] == "table" and len(b["rows"]) > 1:
                head = [clean_text(c) for c in b["rows"][0]]
                for r in b["rows"][1:]:
                    recs.append([{"id": b["id"], "doc": b["doc"], "type": "row",
                                  "cells": dict(zip(head, r)), "html": "", "text": ""}])
        return recs, []
    die("unknown split mode %s" % mode)


def section_blocks(rec, match):
    m = match.lower().rstrip(":")
    for i, b in enumerate(rec):
        if b["type"] == "heading" and b["text"].lower().rstrip(":").startswith(m):
            j = i + 1
            while j < len(rec) and not (rec[j]["type"] == "heading" and rec[j]["level"] <= b["level"]):
                j += 1
            return rec[i + 1:j]
    return None


def keyvalue(rec, key):
    k = key.lower()
    for b in rec:
        if b["type"] == "paragraph":
            m = re.match(r"^\s*([^:]{1,40}):\s*(.+)$", b["text"])
            if m and m.group(1).strip().lower() == k:
                return b, m.group(2).strip()
    return None, None


def convert(value_blocks, spec, shift, warnings, ctx, date_fmt):
    as_ = spec.get("as", "plain")
    if as_ == "richtext":
        return render_blocks(value_blocks, shift)
    text = plain_of(value_blocks) if isinstance(value_blocks, list) else clean_text(value_blocks)
    if as_ == "plain":
        if spec.get("maxlen"):
            text = truncate(text, spec["maxlen"], warnings, ctx)
        return text
    if as_ == "date":
        return parse_date(text, date_fmt, warnings, ctx)
    if as_ == "number":
        try:
            n = float(text.replace(",", ""))
            return int(n) if n.is_integer() else n
        except ValueError:
            warnings.append("not a number '%s' (%s)" % (text, ctx))
            return None
    if as_ == "switch":
        return text.strip().lower() in ("yes", "true", "y", "1", "on")
    if as_ == "list":
        return [x.strip() for x in re.split(r"[,;\n]", text) if x.strip()]
    die("unknown 'as' type %s" % as_)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    allow = "--allow-unclaimed" in sys.argv
    if len(args) != 3:
        die(__doc__)
    ir, mapping, work = load(args[0]), load(args[1]), Path(args[2])
    shift = mapping.get("heading_shift", 0)
    date_fmt = mapping.get("date_format")
    fields = mapping["fields"]
    records, warnings, unclaimed_all, used_slugs = [], [], [], set()
    total_blocks = excluded_count = 0
    used_ids = set()

    for docname, blocks in ir.items():
        excluded = set(mapping.get("exclude_blocks", {}).get(docname, []))
        excluded_count += len(excluded)
        total_blocks += len(blocks)
        recs, pre = split_records(blocks, mapping.get("split", {}), excluded)
        if pre:
            warnings.append("%s: %d block(s) before the first record heading (cover/TOC?) are unclaimed" % (docname, len(pre)))
            unclaimed_all += [(docname, b) for b in pre]
        for rec in recs:
            claimed = set()
            data, ctx = {}, "%s/%s" % (docname, (rec[0].get("text") or "")[:30])
            is_row = rec and rec[0]["type"] == "row"
            order = list(fields.items())
            for slug, spec in order:
                if "const" in spec:
                    data[slug] = spec["const"]
                    continue
                src = spec.get("from")
                if src == "record_title":
                    tb = next((b for b in rec if b["type"] == "heading"), None)
                    if tb is None:
                        warnings.append("%s: no heading found for record_title - using first block" % ctx)
                        tb = rec[0]
                    data[slug] = clean_text(tb.get("text", ""))
                    claimed.add(tb["id"])
                elif src == "slugify":
                    base = data.get(spec["source"], "")
                    s, n = slugify(base), 2
                    cand = s
                    while cand in used_slugs:
                        cand = "%s-%d" % (s, n)
                        n += 1
                    if cand != s:
                        warnings.append("duplicate slug '%s' suffixed to '%s'" % (s, cand))
                    used_slugs.add(cand)
                    data[slug] = cand
                elif src == "column":
                    data[slug] = convert(rec[0]["cells"].get(spec["name"], ""), spec, shift, warnings, ctx, date_fmt)
                elif src == "section":
                    got = section_blocks(rec, spec["match"])
                    if got is None:
                        if spec.get("required"):
                            warnings.append("%s: required section '%s' missing" % (ctx, spec["match"]))
                        continue
                    hd = next(b for b in rec if b["type"] == "heading" and b["text"].lower().rstrip(":").startswith(spec["match"].lower().rstrip(":")))
                    claimed.add(hd["id"])
                    claimed.update(b["id"] for b in got)
                    if spec.get("as", "plain") == "plain" and (len(got) > 3 or any(x["type"] != "paragraph" for x in got)):
                        warnings.append("%s: plain section '%s' spans %d blocks (lists/headings/images flatten into one string) - "
                                        "is a closing heading missing in the source?" % (ctx, spec["match"], len(got)))
                    data[slug] = convert(got, spec, shift, warnings, ctx, date_fmt)
                elif src == "keyvalue":
                    b, v = keyvalue(rec, spec["key"])
                    if b is None:
                        if spec.get("required"):
                            warnings.append("%s: required key '%s' missing" % (ctx, spec["key"]))
                        continue
                    claimed.add(b["id"])
                    data[slug] = convert(v, spec, shift, warnings, ctx, date_fmt)
                elif src == "first_paragraph":
                    b = next((x for x in rec if x["type"] == "paragraph" and x["id"] not in claimed), None)
                    if b:
                        data[slug] = convert([b], spec, shift, warnings, ctx, date_fmt)  # copy, no claim
                elif src == "rest":
                    left = [b for b in rec if b["id"] not in claimed]
                    claimed.update(b["id"] for b in left)
                    data[slug] = convert(left, spec, shift, warnings, ctx, date_fmt)
                else:
                    die("unknown field source '%s' for %s" % (src, slug))
            if is_row:
                claimed = {rec[0]["id"]}
            leftovers = [b for b in rec if b["id"] not in claimed]
            unclaimed_all += [(docname, b) for b in leftovers]
            used_ids.update((docname, i) for i in claimed)
            records.append({"doc": docname, "fieldData": data})

    used_blocks = len(used_ids)
    total_checked = total_blocks - excluded_count
    out = {"records": len(records), "blocks_total": total_blocks, "blocks_excluded": excluded_count,
           "blocks_used": used_blocks, "exclude_reason": mapping.get("exclude_reason"),
           "unclaimed": [{"doc": d, "id": b["id"], "type": b["type"], "preview": (b.get("text") or "")[:60]} for d, b in unclaimed_all],
           "warnings": warnings}
    save(work / "records.json", records)
    save(work / "coverage.json", out)
    print("records=%d  blocks used %d/%d (excluded %d)  warnings=%d  unclaimed=%d" % (
        len(records), used_blocks, total_checked, excluded_count, len(warnings), len(unclaimed_all)))
    for w in warnings:
        print("  warning:", w)
    for d, b in unclaimed_all:
        print("  UNCLAIMED %s [%d] %s: %s" % (d, b["id"], b["type"], (b.get("text") or "")[:60]))
    if unclaimed_all and not allow:
        print("GATE: unclaimed blocks. Extend the mapping, or exclude them by id with a reason.", file=sys.stderr)
        sys.exit(2)
    # required-field warnings are blocking only if the person decides; surfaced above


if __name__ == "__main__":
    main()
