# NFN Labs engineering skills

Team engineering skills for Claude, published as a Claude Code plugin marketplace named
`nfntech`.

> **Prototype for discussion.** The marketplace manifest points at the existing skill folders.
> Nothing has been moved yet. See the plan before relying on any of this.

## What's in it

| Plugin | For | Skills |
|---|---|---|
| `nfn-core` | Everyone (installed automatically with any team plugin) | `engineering-baseline`, `code-review` (placeholders for now) |
| `nfn-backend` | Backend engineers | `backend-engineering` |
| `nfn-react` | React / Next.js engineers | `frontend` (to be renamed `react-engineering`) |
| `nfn-flutter` | Flutter engineers | `flutter-engineering` |
| `nfn-webflow` | Webflow team | `docx-to-webflow-cms` (its scripts are missing; see the review) |

## Install (Claude Code)

```
/plugin marketplace add nfnlabs/nfntech-skill-files
/plugin install nfn-backend@nfntech
```

Swap `nfn-backend` for your team's plugin. `nfn-core` installs with it. To get updates
automatically, open `/plugin`, go to **Marketplaces**, select `nfntech` and turn on auto-update.
Without that, run `/plugin marketplace update nfntech`.

## Change a rule

1. Open a PR that names the incident or review finding behind the change.
2. Bump `version` for the plugin you changed and add a line to `CHANGELOG.md`.
3. The plugin's code owner approves. CI runs `scripts/lint_skills.py` and `claude plugin validate`.

## Conventions

- `SKILL.md` frontmatter uses only `name`, `description` and, when needed, `compatibility`,
  `license`, `metadata` or `allowed-tools`, so the same file works in claude.ai and other tools.
- Descriptions say what the skill owns, when to use it and what it isn't for, in under 600
  characters.
- Companion files have no frontmatter.
