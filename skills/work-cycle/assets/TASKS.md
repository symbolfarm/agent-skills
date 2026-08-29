# Tasks

> **Agents:** read this file at the start of every session, then consult
> `.tasks/LOG.jsonl` for the current task queue. The `work-cycle` skill
> (in `skills/work-cycle/SKILL.md`) describes how to start and complete
> tasks. Use `skills/work-cycle/assets/task-template.md` when creating
> new task files.

## Current focus

<!-- Update this section manually to reflect the current sprint or priority. -->

See `.tasks/LOG.jsonl` for the full queue. Incomplete tasks have a
corresponding file in `.tasks/`.

## Structure

```
.tasks/
├── LOG.jsonl              # Append-only audit log of all tasks
├── debriefs/              # One debrief file per completed task
│   └── task-001-....md
├── task-002-....md        # Pending/active task files (deleted on completion)
└── task-003-....md
```

## Quick reference

| What | Where |
|---|---|
| Full task queue | `.tasks/LOG.jsonl` |
| Active task files | `.tasks/*.md` |
| Completed debriefs | `.tasks/debriefs/` |
| Task template | `skills/work-cycle/assets/task-template.md` |
| Debrief template | `skills/work-cycle/assets/debrief-template.md` |
| Skill instructions | `skills/work-cycle/SKILL.md` |
