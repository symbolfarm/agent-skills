# Portfolio packet execution prompt

Execute exactly one frozen portfolio packet in a fresh unattended session.

- **Plan:** `{{ absolute_plan_path }}`
- **Packet:** `{{ packet_id }}`
- **Project:** `{{ project_id }}`
- **Workdir:** `{{ absolute_project_path }}`
- **Task:** `{{ task_id }}`

Read the committed frozen plan and confirm that this packet still names the
registered project path. Load the packet's attached skills, then read the
project instructions, `TASKS.md`, `.tasks/LOG.jsonl`, and named task file.

Before editing, require all of the following:

1. the task is pending and its dependencies are resolved;
2. the worktree has no unrelated pre-existing changes;
3. the task-file and selected log-entry SHA-256 values match the packet;
4. the current branch and `HEAD` are expected; and
5. the acceptance criteria are concrete enough to execute without questions.

If any check fails, skip the packet and report why. Do not select another task,
guess a decision, or leave the task `in_progress` merely because it was read.

If checks pass, execute only the named task. Follow `task-cycle` through
implementation, tests, debrief, task-log housekeeping, and local commits. Stop
at the packet's stop condition. Never push, merge, rebase, force-update history,
or edit the project-portfolio repository.

Report the packet ID, task ID, result, implementation and housekeeping commits,
verification performed, and any new item requiring user decision or review.