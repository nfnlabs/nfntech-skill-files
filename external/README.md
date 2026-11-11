# External skills

How NFN adopts skills that other teams publish. `registry.json` is the single list of everything
we have considered and who owns each topic. Changes go through PRs reviewed by `@nfnlabs/tech-leads`.

## The rule

**One owner per topic.** If an NFN plugin owns a topic, that skill is the one that's on, and
outside skills on that topic can only be *absorbed*. Only a topic nobody at NFN owns can be
*mirrored*. This stops overlapping skills competing for the same requests.

## Lifecycle

1. **Log it.** Open a PR that adds the source with `"status": "evaluating"`. In Claude Code, ask
   *"evaluate this skill for adoption: <url>"* in this repo; the `skill-intake` skill gathers the
   facts and drafts the entry.
2. **Trial it** on your own machine for about two weeks (the provider's install command, or
   `claude --plugin-dir <clone>`). Nothing is rolled out.
3. **Decide** one of:
   - **mirrored**: an unmodified copy in `plugins/ext-<vendor>-<name>/`, opt-in. Never edit it; CI
     (`scripts/external_skills.py verify`) fails if it differs from upstream.
   - **absorbed**: the rules we want, rewritten into our own companion files with a `Source:` line.
   - **rejected**: the reason, so nobody evaluates it from scratch again.
4. **Upstream changes** (weekly, `.github/workflows/external-skills.yml`):
   - mirrored → a draft PR whose diff is the upstream change. Review it, then merge to ship.
   - absorbed → an issue: "Upstream changed: <id>, anything worth taking?" Close it after moving
     `sha` to the commit you reviewed.
5. **Quarterly:** review each mirror. Retire it if we've absorbed what we need.

## Registry fields

| Field | Meaning |
|---|---|
| `id` | Short name, `<vendor>-<name>` |
| `repo`, `path`, `branch` | Where the skill lives upstream; `path` is the folder holding `SKILL.md` |
| `license` | SPDX id, or `none` |
| `topic` | One key from `topics` |
| `status` | `evaluating`, `mirrored`, `absorbed` or `rejected` |
| `sha` | Mirrored: the commit we copy. Absorbed: the last commit we reviewed |
| `plugin` | Mirrored only: the `ext-*` plugin that holds the copy |
| `absorbed_into` | Absorbed only: our files that took rules from it |
| `owner`, `decided`, `why`, `reason`, `notes` | Who looks after it, when we decided, and why |

## Licenses

MIT, Apache-2.0 and BSD: copy or adapt, keeping the license and notice (mirrors keep the upstream
`LICENSE` file). No license: ideas only, in our own words. Share-alike (CC-BY-SA, GPL): adapted
text keeps that license, so rewrite instead.
