#!/usr/bin/env python3
"""Find external plugins whose upstream has moved past the pinned commit.

Prototype for discussion. Reads .claude-plugin/marketplace.json, and for every entry with a
`github` source pinned by `sha`, asks GitHub for the head of the tracked branch (`ref`, or the
default branch). With --update, rewrites the pins in place and prints a Markdown summary
(compare links) for the pull-request body. Exit 0 always; the workflow decides what to do.

Usage: python3 scripts/check_external_skills.py [--update] [--summary FILE]
Needs GH_TOKEN (any token that can read public repos) to avoid the anonymous rate limit.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

MARKETPLACE = Path(".claude-plugin/marketplace.json")


def api(path: str) -> dict:
    req = urllib.request.Request(f"https://api.github.com/{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if os.environ.get("GH_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GH_TOKEN']}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> int:
    update = "--update" in sys.argv
    summary_path = sys.argv[sys.argv.index("--summary") + 1] if "--summary" in sys.argv else None
    data = json.loads(MARKETPLACE.read_text())
    lines = []
    for entry in data.get("plugins", []):
        src = entry.get("source")
        if not (isinstance(src, dict) and src.get("source") == "github" and src.get("sha")):
            continue
        repo, pinned = src["repo"], src["sha"]
        branch = src.get("ref") or api(f"repos/{repo}")["default_branch"]
        head = api(f"repos/{repo}/commits/{branch}")["sha"]
        if head == pinned:
            print(f"{entry['name']}: up to date at {pinned[:12]}")
            continue
        cmp = api(f"repos/{repo}/compare/{pinned}...{head}")
        files = ", ".join(f["filename"] for f in cmp.get("files", [])[:20])
        print(f"{entry['name']}: {cmp.get('ahead_by', '?')} new commit(s) on {branch}")
        lines.append(
            f"- **{entry['name']}** (`{repo}`): {pinned[:12]} → {head[:12]}, "
            f"{cmp.get('ahead_by', '?')} commit(s). "
            f"[Compare](https://github.com/{repo}/compare/{pinned}...{head})\n"
            f"  - Files: {files or 'n/a'}"
        )
        if update:
            src["sha"] = head
    if update and lines:
        MARKETPLACE.write_text(json.dumps(data, indent=2) + "\n")
    if summary_path:
        Path(summary_path).write_text("\n".join(lines) + ("\n" if lines else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
