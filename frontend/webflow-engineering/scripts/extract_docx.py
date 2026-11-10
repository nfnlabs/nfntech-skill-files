#!/usr/bin/env python3
"""Stage 2 - extract: .docx -> ir.json, outline.txt, extract_report.json.

usage: extract_docx.py WORKDIR file.docx [file2.docx ...] [--media]
                       [--quotes straight|curly] [--ellipsis unicode|dots]

Every <w:t> node in the document is counted and compared with what reached
the IR; anything not reached is listed in extract_report.json as unmatched.
Tracked deletions (<w:del>) are excluded by design and counted.
"""
import argparse
import html
import re
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
from wfcommon import clean_text, save  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
RELNS = "http://schemas.openxmlformats.org/package/2006/relationships"


def q(ns, tag):
    return "{%s}%s" % (ns, tag)


def on(el):
    """OOXML boolean property: present and not explicitly off."""
    if el is None:
        return False
    return el.get(q(W, "val")) not in ("0", "false", "off")


class Doc:
    def __init__(self, path):
        self.path = Path(path)
        self.zip = zipfile.ZipFile(path)
        self.root = ET.fromstring(self.zip.read("word/document.xml"))
        self.rels = self._rels()
        self.styles = self._styles()
        self.numfmt = self._numbering()
        self.visited = set()

    def _rels(self):
        out = {}
        name = "word/_rels/document.xml.rels"
        if name in self.zip.namelist():
            for r in ET.fromstring(self.zip.read(name)).findall(q(RELNS, "Relationship")):
                out[r.get("Id")] = (r.get("Target"), r.get("TargetMode"))
        return out

    def _styles(self):
        out = {}
        if "word/styles.xml" in self.zip.namelist():
            for s in ET.fromstring(self.zip.read("word/styles.xml")).findall(q(W, "style")):
                n = s.find(q(W, "name"))
                out[s.get(q(W, "styleId"))] = (n.get(q(W, "val")) if n is not None else "")
        return out

    def _numbering(self):
        out = {}
        if "word/numbering.xml" not in self.zip.namelist():
            return out
        root = ET.fromstring(self.zip.read("word/numbering.xml"))
        abstract = {}
        for a in root.findall(q(W, "abstractNum")):
            lv = {}
            for l in a.findall(q(W, "lvl")):
                f = l.find(q(W, "numFmt"))
                lv[l.get(q(W, "ilvl"))] = f.get(q(W, "val")) if f is not None else "bullet"
            abstract[a.get(q(W, "abstractNumId"))] = lv
        for n in root.findall(q(W, "num")):
            ref = n.find(q(W, "abstractNumId"))
            if ref is not None:
                out[n.get(q(W, "numId"))] = abstract.get(ref.get(q(W, "val")), {})
        return out


def heading_level(doc, ppr):
    if ppr is None:
        return None
    st = ppr.find(q(W, "pStyle"))
    if st is None:
        return None
    name = doc.styles.get(st.get(q(W, "val")), st.get(q(W, "val"))) or ""
    m = re.match(r"(?i)^heading\s*([1-6])$", name.strip()) or re.match(r"(?i)^heading([1-6])$", st.get(q(W, "val")))
    if m:
        return int(m.group(1))
    if name.strip().lower() == "title":
        return 1
    return None


def run_segments(doc, p):
    """Return [(text, bold, italic, href)] for a paragraph."""
    segs = []

    def walk(node, href=None):
        for ch in node:
            tag = ch.tag
            if tag == q(W, "del"):
                doc.deleted = getattr(doc, "deleted", 0) + len(list(ch.iter(q(W, "delText"))))
                continue
            if tag == q(W, "hyperlink"):
                rid = ch.get(q(R, "id"))
                tgt = doc.rels.get(rid, (None, None))[0] if rid else None
                walk(ch, tgt or href)
            elif tag in (q(W, "ins"), q(W, "smartTag"), q(W, "sdt"), q(W, "sdtContent")):
                walk(ch, href)
            elif tag == q(W, "r"):
                rpr = ch.find(q(W, "rPr"))
                b = on(rpr.find(q(W, "b"))) if rpr is not None else False
                i = on(rpr.find(q(W, "i"))) if rpr is not None else False
                txt = ""
                for c in ch:
                    if c.tag == q(W, "t"):
                        doc.visited.add(id(c))
                        txt += c.text or ""
                    elif c.tag == q(W, "tab"):
                        txt += " "
                    elif c.tag in (q(W, "br"), q(W, "cr")):
                        txt += "\n"
                if txt:
                    segs.append((txt, b, i, href))

    walk(p)
    return segs


def render_inline(segs, fmt):
    # merge adjacent identical formatting, so a bold phrase is one tag
    merged = []
    for t, b, i, h in segs:
        if merged and merged[-1][1:] == (b, i, h):
            merged[-1] = (merged[-1][0] + t, b, i, h)
        else:
            merged.append((t, b, i, h))
    out = []
    for t, b, i, h in merged:
        t = t.replace(" ", " ")
        lead = t[: len(t) - len(t.lstrip(" "))]
        trail = t[len(t.rstrip(" ")):]
        core = html.escape(t.strip(" "), quote=False).replace("\n", "<br>")
        if core:
            if i:
                core = "<em>%s</em>" % core
            if b:
                core = "<strong>%s</strong>" % core
            if h:
                core = '<a href="%s">%s</a>' % (html.escape(h, quote=True), core)
        out.append(lead + core + trail)
    s = "".join(out)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r" +([,.;:!?])", r"\1", s)
    s = fmt(s)
    return s.strip()


def make_fmt(quotes, ellipsis):
    def fmt(s):
        if quotes == "straight":
            s = s.translate({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"'})
        if ellipsis == "dots":
            s = s.replace("…", "...")
        elif ellipsis == "unicode":
            s = s.replace("...", "…")
        return s
    return fmt


def plain(h):
    return clean_text(html.unescape(re.sub(r"<[^>]+>", "", h)))


def para_images(doc, p, media_dir, docname, seq):
    imgs = []
    for d in p.iter(q(W, "drawing")):
        blip = next(d.iter(q(A, "blip")), None)
        if blip is None:
            continue
        rid = blip.get(q(R, "embed"))
        tgt = doc.rels.get(rid, (None, None))[0]
        pr = next(d.iter(q(WP, "docPr")), None)
        alt = (pr.get("descr") or "") if pr is not None else ""
        saved = None
        if tgt and media_dir is not None:
            member = "word/" + tgt.lstrip("/")
            if member in doc.zip.namelist():
                seq[0] += 1
                saved = "media/%s-%d%s" % (Path(docname).stem, seq[0], Path(tgt).suffix)
                (media_dir.parent / saved).write_bytes(doc.zip.read(member))
        imgs.append({"src": saved or tgt, "alt": alt})
    return imgs


def extract(path, media_dir, fmt):
    doc = Doc(path)
    body = doc.root.find(q(W, "body"))
    blocks, seq = [], [0]
    docname = Path(path).name

    def add(**kw):
        kw["id"] = len(blocks)
        kw["doc"] = docname
        blocks.append(kw)

    def handle_p(p):
        ppr = p.find(q(W, "pPr"))
        segs = run_segments(doc, p)
        h = render_inline(segs, fmt)
        imgs = para_images(doc, p, media_dir, docname, seq)
        lvl = heading_level(doc, ppr)
        num = ppr.find(q(W, "numPr")) if ppr is not None else None
        if h or imgs:
            if lvl and h:
                add(type="heading", level=lvl, html=h, text=plain(h))
            elif num is not None and num.find(q(W, "numId")) is not None and h:
                nid = num.find(q(W, "numId")).get(q(W, "val"))
                il = num.find(q(W, "ilvl"))
                il = il.get(q(W, "val")) if il is not None else "0"
                f = doc.numfmt.get(nid, {}).get(il, "bullet")
                add(type="list_item", ordered=f not in ("bullet", "none"), depth=int(il),
                    html=h, text=plain(h))
            elif h:
                add(type="paragraph", html=h, text=plain(h))
            for im in imgs:
                add(type="image", src=im["src"], alt=im["alt"], html="", text="")

    for el in body:
        if el.tag == q(W, "p"):
            handle_p(el)
        elif el.tag == q(W, "tbl"):
            rows = []
            for tr in el.findall(q(W, "tr")):
                cells = []
                for tc in tr.findall(q(W, "tc")):
                    parts = [render_inline(run_segments(doc, p), fmt) for p in tc.findall(q(W, "p"))]
                    cells.append(" ".join(x for x in parts if x))
                rows.append(cells)
            add(type="table", rows=rows, html="", text=" | ".join(" ; ".join(r) for r in rows))
    return doc, blocks


def other_parts(doc):
    """Text outside document.xml. Footnotes/endnotes are content and are returned as
    unmatched fragments (they trip the gate); headers, footers and comments are
    reported by name and count as deliberately ignored."""
    notes, ignored = [], {}
    for name in doc.zip.namelist():
        if not name.startswith("word/") or not name.endswith(".xml"):
            continue
        base = name[5:]
        kind = ("note" if base in ("footnotes.xml", "endnotes.xml") else
                "ignored" if re.match(r"(header|footer)\d*\.xml$|comments\.xml$", base) else None)
        if not kind:
            continue
        root = ET.fromstring(doc.zip.read(name))
        texts = [(t.text or "") for t in root.iter(q(W, "t")) if (t.text or "").strip()]
        if not texts:
            continue
        if kind == "note":
            notes += ["[%s] %s" % (base, t[:70]) for t in texts]
        else:
            ignored[base] = len(texts)
    return notes, ignored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("docx", nargs="+")
    ap.add_argument("--media", action="store_true")
    ap.add_argument("--quotes", choices=["straight", "curly"])
    ap.add_argument("--ellipsis", choices=["unicode", "dots"])
    a = ap.parse_args()
    work = Path(a.workdir)
    work.mkdir(parents=True, exist_ok=True)
    media_dir = None
    if a.media:
        media_dir = work / "media"
        media_dir.mkdir(exist_ok=True)
    fmt = make_fmt(a.quotes, a.ellipsis)

    ir, report, outline = {}, {"documents": {}}, []
    for f in a.docx:
        doc, blocks = extract(f, media_dir, fmt)
        total = list(doc.root.iter(q(W, "t")))
        un = [t for t in total if id(t) not in doc.visited]
        notes, ignored = other_parts(doc)
        name = Path(f).name
        ir[name] = blocks
        report["documents"][name] = {
            "w_t_nodes": len(total),
            "reached_ir": len(total) - len(un),
            "unmatched": len(un) + len(notes),
            "unmatched_fragments": [(t.text or "")[:80] for t in un[:20]] + notes[:20],
            "ignored_parts": ignored,
            "nested_list_items_flattened": sum(1 for b in blocks if b["type"] == "list_item" and b.get("depth", 0) > 0),
            "tracked_deletions_excluded": getattr(doc, "deleted", 0),
            "blocks": len(blocks),
            "images": sum(1 for b in blocks if b["type"] == "image"),
            "images_missing_alt": sum(1 for b in blocks if b["type"] == "image" and not b["alt"]),
        }
        outline.append("== %s ==" % name)
        for b in blocks:
            if b["type"] == "heading":
                outline.append("%s[%d] h%d %s" % ("  " * (b["level"] - 1), b["id"], b["level"], b["text"][:90]))
    save(work / "ir.json", ir)
    save(work / "extract_report.json", report)
    (work / "outline.txt").write_text("\n".join(outline) + "\n", encoding="utf-8")
    bad = 0
    for n, r in report["documents"].items():
        print("%s: blocks=%d unmatched=%d deletions_excluded=%d images=%d (no alt: %d)" % (
            n, r["blocks"], r["unmatched"], r["tracked_deletions_excluded"], r["images"], r["images_missing_alt"]))
        if r["ignored_parts"]:
            print("  note: ignored parts (headers/footers/comments) with text: %s" % r["ignored_parts"])
        if r["nested_list_items_flattened"]:
            print("  warning: %d nested list item(s) flattened to one list level - check the rendered list" % r["nested_list_items_flattened"])
        bad += r["unmatched"]
    if bad:
        print("GATE: unmatched text present - open extract_report.json before continuing", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
