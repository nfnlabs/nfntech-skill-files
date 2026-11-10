"""Shared helpers for the docx -> Webflow CMS import scripts (stdlib only)."""
import html
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

NBSP = " "
ZW = "​‌‍﻿"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def clean_text(s):
    """Normalise whitespace without touching wording."""
    s = s.replace(NBSP, " ")
    for z in ZW:
        s = s.replace(z, "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" +([,.;:!?])", r"\1", s)
    return s.strip()


def canon(s):
    """Canonical comparison form: strip tags, decode entities, fold typography."""
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = s.translate({
        0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"',
        0x2013: "-", 0x2014: "-", 0x2026: "...",
    })
    s = s.replace(NBSP, " ")
    return re.sub(r"\s+", " ", s).strip()


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower())
    return s.strip("-") or "item"


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)
