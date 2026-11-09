#!/usr/bin/env python3
"""Lint the skills and plugin manifests in this repo.

Prototype for discussion. Checks:
  1. Every SKILL.md has YAML frontmatter with only keys that claude.ai uploads and the
     Agent Skills spec accept, a valid `name` that matches its folder, and a
     `description` within the hard limit (1,024 chars) and the team target (600).
  2. Companion/reference files have no frontmatter (they are files a skill opens, not skills).
  3. Every `companions/`, `references/` or `scripts/` path a skill mentions exists inside it.
  4. No zipped skill archives (*.skill, *.zip) are committed.
  5. marketplace.json and every plugin.json parse; each listed plugin has a version, and
     every dependency names a plugin in this marketplace.

Exit code 1 on any error. Warnings never fail the build.
Usage: python3 scripts/lint_skills.py [--report-only] [repo_root]
  --report-only  print findings but exit 0 (used until the migration lands)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml  # PyYAML; installed by the CI workflow

# Keys accepted by the Agent Skills spec and by claude.ai skill uploads.
# Claude Code accepts more (e.g. disable-model-invocation); we stay portable on purpose.
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESC_HARD_MAX = 1024  # platform.claude.com Agent Skills overview: "Maximum 1,024 characters"
DESC_TARGET = 600  # team convention, leaves room and keeps per-turn context small
RESERVED = ("anthropic", "claude")
REF_RE = re.compile(r"(?<![\w/.-])((?:companions|references|scripts)/[A-Za-z0-9_./-]+[A-Za-z0-9_])")
SKIP_DIRS = {".git", "node_modules", "evals"}

errors: list[str] = []
warnings: list[str] = []


def err(path: Path, msg: str) -> None:
    errors.append(f"ERROR  {path}: {msg}")


def warn(path: Path, msg: str) -> None:
    warnings.append(f"WARN   {path}: {msg}")


def frontmatter(text: str):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    return yaml.safe_load(text[4:end]) or {}


def walk(root: Path, pattern: str):
    for p in sorted(root.rglob(pattern)):
        parts = p.relative_to(root).parts
        if any(part in SKIP_DIRS for part in parts):
            continue
        # External mirrors (plugins/ext-*) are upstream's files, checked by
        # `scripts/external_skills.py verify` instead of our house rules.
        if len(parts) > 1 and parts[0] == "plugins" and parts[1].startswith("ext-"):
            continue
        yield p


def lint_skill(skill_md: Path, root: Path) -> None:
    rel = skill_md.relative_to(root)
    text = skill_md.read_text(encoding="utf-8")
    try:
        fm = frontmatter(text)
    except yaml.YAMLError as e:
        err(rel, f"frontmatter is not valid YAML: {e}")
        return
    if fm is None:
        err(rel, "missing YAML frontmatter")
        return
    extra = set(fm) - ALLOWED_KEYS
    if extra:
        err(rel, f"frontmatter keys not accepted everywhere: {sorted(extra)}")
    name, desc = fm.get("name"), fm.get("description")
    folder = skill_md.parent.name
    if not isinstance(name, str) or not NAME_RE.match(name) or len(name) > NAME_MAX:
        err(rel, f"name {name!r} must be lower-case words joined by hyphens, max {NAME_MAX} chars")
    elif any(w in name for w in RESERVED):
        err(rel, f"name {name!r} contains a reserved word")
    elif name != folder:
        warn(rel, f"name {name!r} does not match its folder {folder!r}")
    if not isinstance(desc, str) or not desc.strip():
        err(rel, "description is missing")
    else:
        if len(desc) > DESC_HARD_MAX:
            err(rel, f"description is {len(desc)} chars (limit {DESC_HARD_MAX})")
        elif len(desc) > DESC_TARGET:
            warn(rel, f"description is {len(desc)} chars (team target {DESC_TARGET})")
        if "<" in desc and ">" in desc:
            err(rel, "description must not contain XML tags")

    skill_root = skill_md.parent
    for md in walk(skill_root, "*.md"):
        if md != skill_md and md.name == "SKILL.md":
            continue  # a nested skill is linted on its own
        body = md.read_text(encoding="utf-8")
        if md != skill_md and body.startswith("---\n"):
            warn(md.relative_to(root), "companion file has frontmatter; drop it (only SKILL.md is a skill)")
        for ref in sorted(set(REF_RE.findall(body))):
            target = skill_root / ref.rstrip("/")
            # Repo-local skills (.claude/skills/*) aren't packaged, so they may reference repo files.
            repo_local = rel.parts[:2] == (".claude", "skills")
            if not target.exists() and not (repo_local and (root / ref.rstrip("/")).exists()):
                err(md.relative_to(root), f"references {ref}, which does not exist in {skill_root.relative_to(root)}/")


def lint_manifests(root: Path) -> None:
    mp_path = root / ".claude-plugin" / "marketplace.json"
    if not mp_path.exists():
        warn(Path(".claude-plugin/marketplace.json"), "no marketplace manifest yet")
        return
    try:
        mp = json.loads(mp_path.read_text())
    except json.JSONDecodeError as e:
        err(mp_path.relative_to(root), f"invalid JSON: {e}")
        return
    names = {p.get("name") for p in mp.get("plugins", [])}
    for key in ("name", "owner", "plugins"):
        if key not in mp:
            err(mp_path.relative_to(root), f"missing required field {key!r}")
    for entry in mp.get("plugins", []):
        src = entry.get("source")
        if not (isinstance(src, str) and src.startswith("./")):
            continue  # remote sources are checked by `claude plugin validate`
        pdir = (root / src).resolve()
        pj = pdir / ".claude-plugin" / "plugin.json"
        manifest = {}
        if pj.exists():
            try:
                manifest = json.loads(pj.read_text())
            except json.JSONDecodeError as e:
                err(pj.relative_to(root), f"invalid JSON: {e}")
                continue
        # No plugin.json is fine: the marketplace entry then serves as the manifest.
        if not (manifest.get("version") or entry.get("version")):
            err(mp_path.relative_to(root), f"{entry.get('name')}: no version in plugin.json or marketplace entry")
        for dep in manifest.get("dependencies", []) or entry.get("dependencies", []) or []:
            dep_name = dep if isinstance(dep, str) else dep.get("name", "")
            dep_name = dep_name.split("@")[0]
            if dep_name not in names:
                err(mp_path.relative_to(root), f"{entry.get('name')}: dependency {dep_name!r} is not in this marketplace")


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--report-only"]
    report_only = "--report-only" in sys.argv[1:]
    root = Path(args[0] if args else ".").resolve()
    for skill_md in walk(root, "SKILL.md"):
        lint_skill(skill_md, root)
    for pattern in ("*.skill", "*.zip"):
        for archive in walk(root, pattern):
            err(archive.relative_to(root), "zipped skill committed; build archives in CI instead")
    lint_manifests(root)
    for line in warnings + errors:
        print(line)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors and not report_only else 0


if __name__ == "__main__":
    sys.exit(main())
