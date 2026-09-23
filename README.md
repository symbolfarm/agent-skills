# agent-skills

Reusable, agent-agnostic [skills](https://docs.claude.com/en/docs/claude-code/skills)
authored by [Symbol Farm](https://symbolfarm.com). Each skill is a self-contained
directory under [`skills/`](./skills) holding a `SKILL.md` (the instructions, with
YAML frontmatter), any `assets/` it ships, and its own `LICENSE.txt`.

The skill content is plain Markdown with no hard dependency on any single agent
runtime, so the same source can drive Claude Code, gemini-cli, codex, or anything
else that loads instruction files. Discovery differs per agent (see **Install**).

## Status: experimental

**These skills are experimental, developed for our own use, and change without
warning.** There is no stability guarantee, no deprecation policy, and no
migration path between revisions — instructions get rewritten whenever we learn
something, and a skill can change shape or disappear entirely between commits.
They are published because someone may find them useful to read or adapt, not as
a product.

If you want to depend on them, pin a revision and treat your copy as yours:

```bash
git checkout <tag-or-sha>
```

Issues and pull requests are welcome but may go unanswered.

### A note on the portfolio skills

`portfolio-cycle`, `portfolio-brief` and `work-cycle` assume a **separate,
private portfolio repository** holding `WORKFLOW.md`, `QUEUE.json`, `WORKERS.json`, `PROJECTS.json`,
`CALIBRATION.md` (with its `CALIBRATION-EVIDENCE.md` ledger), `OWNER.md` and
`log/`. That repository is where anything
specific to you belongs: real project names, schedules, delegated authority, and
what only you can do. Keep this repository generic — it is public, and the
portfolio is the half that is not.

**Public/private rule: mechanisms go in this public repository; motivating
examples stay in the private portfolio.** The examples here are invented for
that reason. `scripts/check-public-boundary.py` enforces generic markers and can
read checkout-private terms from `.git/info/public-boundary-denylist` or from the
file named by `PUBLIC_BOUNDARY_DENYLIST`. Those files remain local; diagnostics
report only a term number and never echo the private value.

Install the repository-owned hook for this checkout:

```bash
git config core.hooksPath .githooks
```

The hook scans blobs exactly as staged in Git, so a clean worktree copy cannot
hide a private value left in a partial staging area. The tracked
`.pre-commit-config.yaml` provides the same staged check for contributors who
already use `pre-commit`; it is not required by the local hook above. Neither
route uploads the private denylist or scans the private portfolio.

`scripts/repo_availability.py` is the other half of that split: `work-cycle`
needs to know whether a repository can be edited right now — clean worktree, no
live `.tasks/.lock` from another agent — and that check is a mechanism, so it
lives here. Run it over the repositories a queue names to see which items a run
must skip:

```bash
python3 scripts/repo_availability.py ../repo-a ../repo-b --holder claude
```

It exits non-zero when any named repository is unavailable. Tests:
`python3 -m unittest discover -s tests -t .`

## Current workflow

Themes preserve direction; authorized charters bound independent work;
requirements state observable outcomes; tasks preserve context-sized handoffs.
The private portfolio's `WORKFLOW.md` records its adopted rules and `QUEUE.json`
orders its fresh charters. Historical queues are reference material only.

| Skill | Responsibility |
| --- | --- |
| `portfolio-cycle` | Discuss direction and draft/authorize charters with the user. |
| `charter-cycle` | Select and execute requirements, with atomic claims and evidence. |
| `work-cycle` | Carry out direct requests and implementation work. |
| `research-notebook` | Preserve research findings and current qualified understanding. |
| `digest` | Transfer meaningful changes to their reader. |
| `portfolio-brief` | Report consequences and blockers between reviews. |

`scripts/charter_queue.py` selects from the fresh queue, acquires repository locks,
generates task parent links and checks requirement closeout. Its schema is in
`skills/portfolio-cycle/references/fresh-queue.md`. Direct interactive requests
remain supported without creating a charter. No historical task migration is needed.

## Tools

Small standard-library programs the skills and their sites rely on. They have
**no runtime dependencies** and are meant to be run from a checkout, not
installed.

| Tool | What it does |
| --- | --- |
| [`tools/build_pages.py`](./tools/build_pages.py) | Build a committed static site — explainer and document pages — from a JSON config: Markdown to HTML, audited inline-SVG passthrough, three named block components, optional build-time stylesheet inlining, declared asset copying, `.md`→`.html` route rewriting, and explainer-metadata validation. `--check` fails when the committed output is not byte-reproducible. |
| [`scripts/repo_availability.py`](./scripts/repo_availability.py) | Report whether repositories are clean and unlocked, so one blocked repository costs one queue item rather than the run. |
| [`scripts/check-public-boundary.py`](./scripts/check-public-boundary.py) | Guard what this public repository may contain. |

`build_pages.py` carries no site of its own: every path in a site config
resolves relative to that config, so the site lives in its repository and the
builder lives here. Run it from the site's checkout —

```bash
python3 ../agent-skills/tools/build_pages.py --check
python3 ../agent-skills/tools/build_pages.py --config site/site.json
```

— where `--config` defaults to `site.json` or `site/site.json` under the
working directory. Beyond ordinary Markdown it renders a **closed set of three
block components** as fenced `` ```:reading ``, `` ```:option `` and
`` ```:status `` directives — the best-reading/alternative pair, the option card
with a verdict, and the status pill row — taking its class names from the
hand-authored digest pages of 2026-09-16 so existing stylesheets keep working.
The set is closed: an unknown or malformed directive fails the build naming the
file and line rather than passing markup through, which is what keeps the audited
inline-SVG block the only unescaped markup in output. Growing the set needs a
page that cannot say something without a fourth component. A config may also set
`inline_stylesheet` to one stylesheet, embedded in every output document so a
single file renders standalone; omitting it keeps the linked `stylesheet`. It was consolidated here on 2026-09-12 from
`adus-intelligence`, which had the only reusable of five separate rendering
approaches; its behaviour was moved unchanged, and its end-to-end test against
that site's committed pages skips when that checkout is not beside this one.

## Install

There is no universal cross-agent install command — each agent discovers skills
from its own directory. Keep a local clone of this repo as the canonical source
and link the skills you want into the relevant agent's skills directory.

### Claude Code

Claude Code auto-discovers any folder containing a `SKILL.md` under
`~/.claude/skills/`. Symlink the skills you want (per-skill, so you can enable
them selectively):

```bash
git clone https://github.com/symbolfarm/agent-skills.git
ln -s "$PWD/agent-skills/skills/work-cycle" ~/.claude/skills/work-cycle
```

Use a project-local `.claude/skills/` instead of `~/.claude/skills/` to scope a
skill to a single repo.

### Hermes Agent

Keep this repository as the canonical checkout and add its `skills/` directory
to `skills.external_dirs` in the active Hermes profile's `config.yaml`:

```yaml
skills:
  external_dirs:
    - /absolute/path/to/agent-skills/skills
```

Start a new Hermes session after configuring the directory. The skills then
appear in `skills_list`, `skill_view`, slash commands, and cron skill
attachments while edits continue to land in this Git working tree.

### Other agents

Point the agent at the same canonical `skills/<name>/` directory using its own
mechanism (e.g. gemini-cli extensions, or copying the instructions into an
`AGENTS.md`-style file). The skill content is portable; only the link target
changes.

## Versioning

Each skill carries a `version` in its `SKILL.md` frontmatter. Tag releases so
consumers can pin a known-good revision (`git checkout <tag>`) rather than
tracking `main`.

## License

MIT — see [`LICENSE`](./LICENSE) at the root, and each skill's own
`LICENSE.txt` for skills vendored individually.
