#!/usr/bin/env python3
"""Stage 6a - verify: records.json vs items read back from Webflow.

usage: verify_items.py RECORDS ITEMS_LIVE WORKDIR

ITEMS_LIVE is the raw saved JSON from list_collection_items (an item list, a
{"items": [...]} response, or a list of such responses). Items match records
by slug. Per field it checks existence, canonical text equality, character
count, the final 40 characters and block count, so a missing paragraph, a
mid-field deletion and a truncated tail are separate findings.
Exit 0 = every record clean, 1 = problems.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wfcommon import canon, die, load  # noqa: E402

BLOCK = re.compile(r"<(p|h[1-6]|li|blockquote|figure|table)\b", re.I)


def flatten(raw):
    items = []
    stack = [raw]
    while stack:
        x = stack.pop()
        if isinstance(x, list):
            stack.extend(x)
        elif isinstance(x, dict):
            if "fieldData" in x:
                items.append(x)
            else:
                for k in ("items", "data", "result", "results"):
                    if k in x:
                        stack.append(x[k])
    return items


def cmp_field(slug, want, got, problems):
    if got is None:
        problems.append("%s: missing in live item" % slug)
        return
    if isinstance(want, str):
        cw, cg = canon(want), canon(got if isinstance(got, str) else str(got))
        if cw != cg:
            if len(cw) != len(cg):
                problems.append("%s: length differs (want %d, live %d)" % (slug, len(cw), len(cg)))
            if cw[-40:] != cg[-40:]:
                problems.append("%s: tail differs (want ...%r, live ...%r) - truncation?" % (slug, cw[-40:], cg[-40:]))
            if len(cw) == len(cg):
                i = next((k for k in range(len(cw)) if cw[k] != cg[k]), 0)
                problems.append("%s: text differs at char %d (want %r, live %r)" % (slug, i, cw[i:i + 20], cg[i:i + 20]))
            elif cw[:40] != cg[:40] and cw[-40:] == cg[-40:]:
                problems.append("%s: head differs (want %r, live %r)" % (slug, cw[:40], cg[:40]))
        if "<" in want and len(BLOCK.findall(want)) != len(BLOCK.findall(got if isinstance(got, str) else "")):
            problems.append("%s: block count differs (want %d, live %d)" % (
                slug, len(BLOCK.findall(want)), len(BLOCK.findall(got if isinstance(got, str) else ""))))
    elif want != got:
        problems.append("%s: value differs (want %r, live %r)" % (slug, want, got))


def main():
    if len(sys.argv) != 4:
        die(__doc__)
    records, live, work = load(sys.argv[1]), flatten(load(sys.argv[2])), Path(sys.argv[3])
    by_slug = {}
    for it in live:
        s = (it.get("fieldData") or {}).get("slug")
        if s:
            by_slug.setdefault(s, []).append(it)
    lines, clean, bad = ["# Verify report", ""], 0, 0
    for rec in records:
        want = rec["fieldData"]
        slug = want.get("slug")
        problems = []
        hits = by_slug.get(slug, [])
        if not hits:
            problems.append("no live item with slug '%s' (slug rewritten, not created, or not all pages read)" % slug)
        else:
            if len(hits) > 1:
                problems.append("%d live items share slug '%s' (duplicate create?)" % (len(hits), slug))
            got = hits[0]["fieldData"]
            for k, v in want.items():
                if k != "slug":
                    cmp_field(k, v, got.get(k), problems)
        if problems:
            bad += 1
            lines.append("## %s - %d problem(s)" % (slug, len(problems)))
            lines += ["- " + p for p in problems]
        else:
            clean += 1
    extra = [s for s in by_slug if s not in {r["fieldData"].get("slug") for r in records}]
    lines += ["", "Live items not in records (pre-existing or stray): %d" % len(extra)]
    summary = "verified %d records: %d clean, %d problems" % (len(records), clean, bad)
    lines.insert(1, summary)
    (work / "verify_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
