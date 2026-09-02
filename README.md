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
private portfolio repository** holding `GOALS.md`, `PROJECTS.json`,
`CALIBRATION.md`, `OWNER.md` and `log/`. That repository is where anything
specific to you belongs: real project names, schedules, delegated authority, and
what only you can do. Keep this repository generic — it is public, and the
portfolio is the half that is not.

**Public/private rule: mechanisms go in this public repository; motivating
examples stay in the private portfolio.** The examples here are invented for
that reason. `scripts/check-public-boundary.py` enforces a baseline denylist at
pre-commit time and can read additional local terms from the Git metadata
directory without committing those private terms.

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

## Skills

| Skill | What it does |
| --- | --- |
| [`work-cycle`](./skills/work-cycle) | Execute one durable item: claim and deliver a portfolio goal, or start, complete, and debrief a repository implementation task. |
| [`research-notebook`](./skills/research-notebook) | Maintain the living research record: dated lab logs, experiment and source notes, current claims, and explicit correction/supersession. |
| [`portfolio-cycle`](./skills/portfolio-cycle) | Run the interactive review, teach research state in depth, set direction, re-order goals, allocate tasks to agents and people, and update project and calibration state. |
| [`portfolio-brief`](./skills/portfolio-brief) | Produce the recurring concise report: progress, delegated decisions, artifacts to try, queue state, and bounded unfiled proposals. |

The operating model has one portfolio-owned outcome queue and repository-owned
implementation tasks. `work-cycle` executes either kind; `portfolio-cycle`
handles review, scoping, research learning and allocation; `research-notebook`
holds findings; and `portfolio-brief` is the light recurring report. Executable
human work is represented as assignee-marked items in the same derived view,
not as a second checklist. Delegation remains keyed by decision class in the
private portfolio's calibration ledger rather than being copied onto items.

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
