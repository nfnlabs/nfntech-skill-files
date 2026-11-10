#!/usr/bin/env python3
"""Self-test for the import scripts: builds synthetic .docx files and runs the
whole pipeline. usage: python selftest.py   (exit 0 = all checks passed)"""
import copy
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"')


def p(t, style=None, num=False):
    s = '<w:pStyle w:val="%s"/>' % style if style else ""
    n = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>' if num else ""
    return "<w:p><w:pPr>%s%s</w:pPr>%s</w:p>" % (s, n, t)


def r(t, b=False):
    return '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % ("<w:b/>" if b else "", t)


def docx(path, body, extra=None):
    styles = '<?xml version="1.0"?><w:styles %s>%s</w:styles>' % (NS, "".join(
        '<w:style w:styleId="Heading%d"><w:name w:val="heading %d"/></w:style>' % (i, i) for i in (1, 2, 3)))
    num = ('<?xml version="1.0"?><w:numbering %s><w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0">'
           '<w:numFmt w:val="bullet"/></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/>'
           "</w:num></w:numbering>" % NS)
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId9" Type="x" Target="media/image1.png"/></Relationships>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", '<?xml version="1.0"?><w:document %s><w:body>%s</w:body></w:document>' % (NS, body))
        z.writestr("word/styles.xml", styles)
        z.writestr("word/numbering.xml", num)
        z.writestr("word/_rels/document.xml.rels", rels)
        z.writestr("word/media/image1.png", b"\x89PNG")
        for k, v in (extra or {}).items():
            z.writestr(k, v)


def run(*args):
    return subprocess.run([sys.executable, str(HERE / args[0]), *map(str, args[1:])], capture_output=True, text=True)


FAILED = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        FAILED.append(name)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="wf-selftest-"))
    img = ('<w:p><w:r><w:drawing><wp:inline><wp:docPr id="1" name="x" descr="A suitcase"/><a:graphic><a:graphicData>'
           '<a:blip r:embed="rId9"/></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
    body = "".join([
        p(r("Handbook"), "Heading1"), p(r("Travel Policy"), "Heading2"),
        p(r("Author: Priya Nair")), p(r("Date: 04/05/2025")),
        p(r("Summary"), "Heading3"), p(r("Short summary here.")), p(r("Details"), "Heading3"),
        p(r("Staff must ") + r("book", True) + r(" early", True) + r(" and keep receipts.")),
        p(r("Item one"), None, True), p(r("Item two"), None, True),
        '<w:p><w:del w:id="1"><w:r><w:delText>gone</w:delText></w:r></w:del><w:r><w:t>kept after deletion</w:t></w:r></w:p>',
        img])
    docx(tmp / "t.docx", body)
    w = tmp / "W"

    e = run("extract_docx.py", w, tmp / "t.docx", "--media")
    ir = json.loads((w / "ir.json").read_text(encoding="utf-8"))["t.docx"]
    html = " ".join(b.get("html", "") for b in ir)
    check("extract: exit 0, nothing unmatched", e.returncode == 0, e.stderr)
    check("extract: split bold runs merge into one <strong>", "<strong>book early</strong>" in html, html)
    check("extract: non-breaking space normalised", " " not in html)
    check("extract: tracked deletion excluded", "gone" not in html)
    check("extract: image alt text captured", any(b["type"] == "image" and b["alt"] == "A suitcase" for b in ir))

    mp = tmp / "map.json"
    mapping = {"split": {"mode": "heading", "level": 2}, "heading_shift": 1,
               "exclude_blocks": {"t.docx": [0]},
               "fields": {"name": {"from": "record_title"}, "slug": {"from": "slugify", "source": "name"},
                          "author": {"from": "keyvalue", "key": "Author", "as": "plain"},
                          "published": {"from": "keyvalue", "key": "Date", "as": "date"},
                          "summary": {"from": "section", "match": "Summary", "as": "plain", "maxlen": 300},
                          "excerpt": {"from": "first_paragraph", "as": "plain", "maxlen": 160},
                          "body": {"from": "rest", "as": "richtext"}}}
    mp.write_text(json.dumps(mapping), encoding="utf-8")
    b = run("build_records.py", w / "ir.json", mp, w)
    check("build: ambiguous 04/05/2025 stops the run", b.returncode != 0 and "AMBIGUOUS DATE" in b.stderr, b.stderr)
    mapping["date_format"] = "dmy"
    mp.write_text(json.dumps(mapping), encoding="utf-8")
    b = run("build_records.py", w / "ir.json", mp, w)
    rec = json.loads((w / "records.json").read_text(encoding="utf-8"))[0]["fieldData"]
    check("build: exit 0 with date_format", b.returncode == 0, b.stdout + b.stderr)
    check("build: date parsed D/M", rec["published"] == "2025-05-04T00:00:00.000Z", rec.get("published"))
    check("build: first_paragraph copies without claiming (appears in body too)",
          rec["excerpt"].startswith("Staff must") and "Staff must" in rec["body"])
    check("build: headings shifted by 1", "<h4>Details</h4>" in rec["body"], rec["body"])

    schema = tmp / "schema.json"
    schema.write_text(json.dumps({"fields": [
        {"slug": "name", "type": "PlainText", "isRequired": True}, {"slug": "slug", "type": "PlainText", "isRequired": True},
        {"slug": "author", "type": "PlainText"}, {"slug": "published", "type": "DateTime"},
        {"slug": "summary", "type": "PlainText"}, {"slug": "excerpt", "type": "PlainText"},
        {"slug": "body", "type": "RichText"}]}), encoding="utf-8")
    v = run("validate_records.py", w / "records.json", schema, w)
    check("validate: local image path is an error", v.returncode == 1 and "local/Word path" in v.stdout, v.stdout)
    recs = (w / "records.json").read_text(encoding="utf-8").replace("media/t-1.png", "https://cdn.example.com/t-1.png")
    (w / "records.json").write_text(recs, encoding="utf-8")
    v = run("validate_records.py", w / "records.json", schema, w)
    check("validate: passes after URL substituted", v.returncode == 0, v.stdout)

    records = json.loads((w / "records.json").read_text(encoding="utf-8"))
    good = [{"id": "a" * 24, "fieldData": copy.deepcopy(x["fieldData"])} for x in records]
    (tmp / "good.json").write_text(json.dumps({"items": good}), encoding="utf-8")
    bad = copy.deepcopy(good)
    bad[0]["fieldData"]["body"] = bad[0]["fieldData"]["body"].replace("<li>Item two</li>", "").replace("receipts.", "rec")
    (tmp / "bad.json").write_text(json.dumps([{"items": bad}]), encoding="utf-8")
    check("verify: clean read-back passes", run("verify_items.py", w / "records.json", tmp / "good.json", w).returncode == 0)
    vb = run("verify_items.py", w / "records.json", tmp / "bad.json", w)
    rep = (w / "verify_report.md").read_text(encoding="utf-8")
    check("verify: truncation + dropped list item caught", vb.returncode == 1 and "tail differs" in rep and "block count" in rep, rep)

    # regression: whole_doc title is the first heading, not the first block
    docx(tmp / "a.docx", p(r("Intro before title")) + p(r("Real Title"), "Heading1") + p(r("Body.")))
    run("extract_docx.py", tmp / "WA", tmp / "a.docx")
    m2 = tmp / "m2.json"
    m2.write_text(json.dumps({"split": {"mode": "whole_doc"}, "fields": {
        "name": {"from": "record_title"}, "slug": {"from": "slugify", "source": "name"},
        "body": {"from": "rest", "as": "richtext"}}}), encoding="utf-8")
    run("build_records.py", tmp / "WA" / "ir.json", m2, tmp / "WA")
    t = json.loads((tmp / "WA" / "records.json").read_text(encoding="utf-8"))[0]["fieldData"]
    check("regression: whole_doc title is the first heading", t["name"] == "Real Title", t["name"])

    # regression: footnote text must trip the coverage gate
    fn = ('<?xml version="1.0"?><w:footnotes %s><w:footnote w:id="2"><w:p><w:r><w:t>FOOTNOTE TEXT</w:t></w:r></w:p>'
          "</w:footnote></w:footnotes>" % NS)
    docx(tmp / "b.docx", p(r("Title"), "Heading1") + p(r("Body.")), {"word/footnotes.xml": fn})
    fe = run("extract_docx.py", tmp / "WB", tmp / "b.docx")
    check("regression: footnote text is flagged unmatched (exit 2)", fe.returncode == 2, fe.stdout + fe.stderr)

    print("\n%s" % ("ALL CHECKS PASSED" if not FAILED else "FAILED: %s" % FAILED))
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
