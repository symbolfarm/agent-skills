# Portfolio slot execution prompt

This template documents the prompt rendered by `scripts/render_cron_jobs.py`.
The renderer fills the frozen plan path, slot number, project ID, scheduled time,
and project workdir.

The assigned repository is the execution environment. Its `AGENTS.md`, linked
project documents, scripts, and task records are authoritative. Attach only the
generic `task-cycle` skill; do not load a project-specific skill.

Before editing, require:

1. the frozen schema-v2 plan still assigns this slot to this project;
2. the repository contains `AGENTS.md`, `TASKS.md`, and `.tasks/LOG.jsonl`;
3. the worktree is clean and no task is already `in_progress`;
4. a pending, unblocked, concrete task exists; and
5. no user decision or project/portfolio reprioritisation is needed.

If a check fails, make no edits and report a no-op. Never invent, broaden, split,
or reprioritise work. Otherwise complete at most one task through task-cycle,
including tests, debrief, task-log housekeeping, and local commits. Never push,
merge, rebase, or modify the project-portfolio repository.
