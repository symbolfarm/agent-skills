---
name: portfolio-cycle
description: Coordinate an interactive multi-project planning session, shape project-local backlogs, allocate up to twelve expiring two-hour execution slots, render one-shot Hermes cron jobs, and reconcile results. Use for cross-project priority, capacity, user decisions, WhatsApp planning, or unattended portfolio scheduling. Repository state is evidence; discussion remains the source of strategy.
license: MIT
metadata:
  author: Symbol Farm
  version: "4"
  category: productivity
  tags: portfolio, planning, task-cycle, cron, whatsapp, multi-project
---

# Portfolio cycle

Coordinate attention across independent repositories without creating a second
task system. The portfolio layer decides where execution capacity goes. Each
project repository defines what work means and `task-cycle` executes it.

## Non-negotiable boundaries

- Begin with an interactive priority and trade-off discussion.
- Treat Git, task, research, and test state as evidence, not automatic strategy.
- Keep task descriptions, statuses, acceptance criteria, and debriefs in projects.
- Keep project instructions in each repository's `AGENTS.md`, linked docs, and
  scripts. Do not require or generate project-specific Hermes skills.
- Use priorities plus explicit slot allocations; rank alone can starve projects.
- Twelve slots are maximum capacity, never a quota.
- Unattended jobs complete at most one already-filed task per invocation.
- Never let unattended execution invent, broaden, split, or reprioritise work.
- Commit locally only when allowed. Never push unless the user explicitly changes
  the portfolio policy.
- Frozen plans are immutable. Supersede them rather than editing them.
- Use supported Hermes cron APIs; never edit scheduler-internal JSON directly.

## Portfolio repository

Default location: `/workspace/project-portfolio`.

- `PROJECTS.json`: project paths, strategic status, rank, cycle, automation policy,
  daily task limit, and generic skills.
- `PORTFOLIO.md`: concise human-facing dashboard.
- `DECISIONS.md`: user decisions and review requests.
- `plans/YYYY-MM-DD.json`: immutable execution authority once frozen.
- `deployments/YYYY-MM-DD.json`: rendered cron payloads and, after deployment,
  actual scheduler job IDs.
- `reviews/YYYY-MM-DD.md`: verified outcomes and planning lessons.
- `scripts/validate_portfolio.py`: schema and policy validation.
- `scripts/render_cron_jobs.py`: deterministic schema-v2 plan-to-cron rendering.

Projects remain authoritative for `AGENTS.md`, `TASKS.md`, `.tasks/LOG.jsonl`,
active task files, research records, tests, and Git history.

## Phase 0: establish the interactive venue

The session may happen in the current chat or through a gateway such as
WhatsApp. It must be conversational either way.

For a WhatsApp-initiated session, use a one-shot cron kickoff with:

- `workdir: /workspace/project-portfolio`
- `skills: ["portfolio-cycle"]`
- `deliver: whatsapp` or a more specific WhatsApp destination
- `attach_to_session: true`
- a prompt that reads current portfolio evidence, sends a concise opening brief,
  and invites the user to discuss priorities

The kickoff must not freeze a plan, deploy execution jobs, or answer its own
strategy questions. The user's replies continue the attached session.

## Phase 1: collect evidence

Inspect, without yet changing strategy:

1. portfolio registry, latest plan/review, decisions, and deployments;
2. each relevant project's `AGENTS.md`, task queue, research records, Git status,
   recent commits, and validation state;
3. material changes since the prior session;
4. tasks blocked on user decisions or review;
5. dirty, missing, ambiguous, or unsafe repositories.

Summarise only material evidence. Do not mechanically sort the queue and call it
planning.

## Phase 2: hold the priority conversation

Discuss with the user:

- what outcome matters most now;
- changes in urgency, value, risk, dependencies, or available attention;
- whether a primary project should continue receiving most capacity;
- which lower-ranked project deserves protected capacity to avoid starvation;
- what decisions or reviews need the user's attention;
- how much unattended capacity should be used at all;
- the desired first slot time, delivery target, and any quiet-hours constraint.

Questions and proposals do not authorise edits by themselves. Make planning
changes only after the user agrees to them.

## Phase 3: shape project-local backlogs

For projects being considered for execution:

1. enter the repository;
2. read `AGENTS.md` and project documents;
3. use `task-cycle` to add, split, clarify, or prioritise tasks;
4. ensure acceptance criteria, dependencies, `Touches`, and validation commands
   are concrete;
5. separate user decisions from executable work;
6. verify `TASKS.md`, `.tasks/LOG.jsonl`, and referenced task files agree;
7. commit project-local planning changes independently when appropriate.

Do not copy task descriptions or statuses into the portfolio plan. A slot grants
capacity to a project; `task-cycle` chooses the highest-priority pending,
unblocked task at execution time.

## Phase 4: allocate generated slots

Use schema-version 2 for new plans.

- Capacity is at most 12 slots.
- Slot timestamps are derived from one offset-aware `schedule.start_at` value.
- `schedule.interval_hours` is 2.
- Unallocated slots are omitted.
- Multiple slots may target one project, subject to its `daily_task_limit`.
- A frozen slot may target only an active `cron_allowed` project.
- Execution defaults are one task, local commit, no push, stop on ambiguity.
- Initial delivery is normally `whatsapp` when the gateway is configured.

Two-hour spacing reduces but does not eliminate collision risk. Each job must
no-op if the repository is dirty or another task is already `in_progress`.

## Phase 5: freeze and render

Before freezing:

1. record the current registry Git revision;
2. validate project paths beneath `/workspace`;
3. verify allocated repositories contain `AGENTS.md`, `TASKS.md`, and
   `.tasks/LOG.jsonl`;
4. validate the draft plan;
5. show the user the proposed allocation and schedule.

After approval, mark the plan `frozen` and commit it. Render with:

```bash
python3 scripts/validate_portfolio.py .
python3 scripts/render_cron_jobs.py plans/YYYY-MM-DD.json \
  --output deployments/YYYY-MM-DD.json
```

Review the generated manifest before deployment. Rendering has no scheduler side
effect.

## Phase 6: deploy one-shot cron jobs

For every rendered payload, create a Hermes job through the supported cron API.
The generated job must have:

- an ISO one-shot schedule and `repeat: 1`;
- the assigned project as `workdir`;
- only the generic `task-cycle` skill;
- repository-local instructions loaded from `AGENTS.md`;
- at most one task;
- clean-worktree and no-`in_progress` preflight checks;
- local commit and no push;
- a fail-closed no-op on missing work, ambiguity, decisions, or stale allocation.

Record returned job IDs and deployed timestamps in `deployments/`. Do not mutate
the frozen plan. If deployment is partial, record exactly which jobs exist and
pause or remove them through the cron API before retrying.

## Phase 7: reconcile

At the next interactive session:

1. inspect scheduler outcomes and project Git/task state;
2. verify claimed commits, tests, debriefs, and log transitions directly;
3. classify each slot as completed, no-op, blocked, failed, or deferred;
4. add user decisions/reviews to `DECISIONS.md`;
5. write `reviews/YYYY-MM-DD.md`;
6. update the dashboard and registry only after discussion;
7. commit portfolio reconciliation separately from project work.

## Fail-closed conditions

Do not execute or deploy a slot when:

- the plan is draft, invalid, stale, or superseded;
- the project is not active and `cron_allowed`;
- required repository-local instruction/task files are absent;
- the worktree is dirty or a task is already `in_progress`;
- no eligible task exists;
- task scope or acceptance criteria are ambiguous;
- a user decision or external review is required;
- another slot or process is operating in the same repository;
- the renderer output differs from the frozen allocation.

A no-op is a correct result. Never substitute unrelated work.

## Historical schema

Schema-version 1 packet plans remain valid historical execution records and may
retain exact task/source snapshots. Do not rewrite them to match the current
registry. New portfolio plans use generated schema-version 2 slots.
