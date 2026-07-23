# agent-skills

Reusable, agent-agnostic [skills](https://docs.claude.com/en/docs/claude-code/skills)
authored by [Symbol Farm](https://symbolfarm.com). Each skill is a self-contained
directory under [`skills/`](./skills) holding a `SKILL.md` (the instructions, with
YAML frontmatter), any `assets/` it ships, and its own `LICENSE.txt`.

The skill content is plain Markdown with no hard dependency on any single agent
runtime, so the same source can drive Claude Code, gemini-cli, codex, or anything
else that loads instruction files. Discovery differs per agent (see **Install**).

## Skills

| Skill | What it does |
| --- | --- |
| [`task-cycle`](./skills/task-cycle) | Manage the task lifecycle for a repo — find the next task, mark it in-progress, write the debrief, update `LOG.jsonl`, and commit. |
| [`research-notebook`](./skills/research-notebook) | Maintain a project's living research notebook (`notebook/`) — Obsidian-compatible Markdown notes, dated lab logs, experiment records, reference reading notes, and a correction/supersession discipline; interlocks with `task-cycle` via a findings-gated distill step at task completion. |
| [`research-cycle`](./skills/research-cycle) | Drive the research workflow over the notebook: **learning** sessions that sync the human and set direction, **planning** that breaks direction into filed `task-cycle` tasks with pre-registered experiment stubs, and **logging** that closes findings back into the notebook. |
| [`portfolio-cycle`](./skills/portfolio-cycle) | Hold an interactive cross-project priority discussion, shape repository-local backlogs, allocate up to twelve expiring two-hour slots, render one-shot Hermes cron payloads, support continuable WhatsApp planning, and reconcile outcomes without duplicating project task state. |

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
ln -s "$PWD/agent-skills/skills/task-cycle" ~/.claude/skills/task-cycle
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

MIT, per skill — see each skill's `LICENSE.txt`.
