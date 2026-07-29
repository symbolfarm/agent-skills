---
name: portfolio-cycle
description: Coordinate an interactive multi-project planning session, allocate scarce human attention, manage bounded autonomy envelopes, shape project-local backlogs, render one-shot Hermes cron jobs, and reconcile verified outcomes into concise digests. Use for cross-project priority, capacity, user decisions, low-attention operation, WhatsApp planning, or unattended scheduling. Repository state is evidence; discussion remains the source of strategy.
license: MIT
metadata:
  author: Symbol Farm
  version: "5"
  category: productivity
  tags: portfolio, planning, task-cycle, cron, whatsapp, multi-project
---

# Portfolio cycle

Coordinate scarce human attention across independent repositories without
creating a second task system. The portfolio layer decides where execution
capacity goes. Each project repository defines what work means and `task-cycle`
executes it.

## Non-negotiable boundaries

- Begin with an interactive priority and trade-off discussion.
- Treat Git, task, research, and test state as evidence, not automatic strategy.
- Keep task descriptions, statuses, acceptance criteria, and debriefs in projects.
- Keep project instructions in each repository's `AGENTS.md`, linked docs, and
  scripts. Do not require or generate project-specific Hermes skills.
- Limit simultaneous attention lanes; related repositories may form one programme
  lane, and only one incubator should normally be active at a time.
- Use priorities plus explicit slot allocations; rank alone can starve projects.
- Twelve slots are maximum capacity, never a quota.
- Unattended jobs complete at most one task per invocation.
- By default, unattended execution may select only already-filed work and may not
  invent, broaden, split, or reprioritise it. A project may derive and file one
  task only when the user has approved a project-local autonomy envelope that
  explicitly defines the goal, permitted actions, iteration budget, stopping
  conditions, prohibited decisions, and escalation triggers.
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
active task files, autonomy envelopes, research records, tests, and Git history.

## Low-attention operating model

Use this mode when execution throughput exceeds the user's review capacity.

- Count tightly coupled repositories as one programme attention lane.
- Keep at most two active lanes by default: one primary programme and one
  time-bounded incubator. Park other incubators rather than assigning equal turns.
- Choose weekly or fortnightly reconciliation unless urgency justifies a denser
  cadence.
- Execution jobs normally use local delivery. Notify the user immediately only
  for a safety issue, destructive ambiguity, unexpected cost/external exposure,
  or a genuinely blocking decision.
- A later reconciliation job or interactive session verifies all outputs and
  produces one concise digest: material change, verification, recommendation,
  and at most one consequential user decision.
- Review milestones, not commits. Human review is normally reserved for public
  claims or publication, externally visible milestones, difficult-to-reverse
  architecture, spending/provider/privacy/safety choices, or evidence that
  invalidates the current direction.
- An unresolved decision parks its affected lane; it does not accumulate a queue
  of additional questions.

### Project-local autonomy envelopes

An autonomy envelope is an explicit delegation of bounded tactical authority,
not permission to choose product strategy. Store it in the owning repository
and link it from `AGENTS.md`. It must state:

1. the stable outcome or question;
2. actions and file boundaries the agent may initiate without review;
3. objective validation and milestone criteria;
4. maximum derived tasks or iterations before reconciliation;
5. stopping and escalation conditions;
6. prohibited product, research, cost, publication, provider, privacy, safety,
   and difficult-to-reverse architectural decisions.

Within an approved envelope, an unattended steward may file at most one concrete
derived task per invocation, then either stop or let a later task-cycle slot
execute it. It must not both create an open-ended backlog and execute through it.
Outside an approved envelope, the existing filed-task-only rule applies.

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
- whether a primary programme should continue receiving most capacity;
- which single incubator, if any, deserves the other active attention lane;
- which projects should be explicitly parked rather than kept nominally active;
- what decisions or milestone reviews genuinely need the user's attention;
- the decision budget for this cycle (normally zero or one);
- how much unattended capacity should be used at all;
- whether the cadence should be weekly, fortnightly, or temporarily denser;
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
- In low-attention mode, execution delivery defaults to `local`; use WhatsApp for
  the consolidated digest and exceptional escalations. Interactive or
  high-attention cycles may still deliver individual results to WhatsApp.

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

At the next scheduled digest or interactive session:

1. inspect scheduler outcomes and project Git/task state;
2. verify claimed commits, tests, debriefs, and log transitions directly;
3. classify each slot as completed, no-op, blocked, failed, or deferred;
4. distinguish milestones requiring human review from routine verified commits;
5. add only genuinely blocking user decisions/reviews to `DECISIONS.md`;
6. write `reviews/YYYY-MM-DD.md` and update stale project focus text;
7. produce one concise digest containing material change, verification,
   recommendation, and at most one consequential decision;
8. update the dashboard and registry only after approved strategy is clear;
9. commit portfolio reconciliation separately from project work.

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
