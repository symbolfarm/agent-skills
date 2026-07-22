---
name: portfolio-cycle
description: >-
  Coordinate attention across several project repositories without replacing
  their own task-cycle or research-cycle records. Use when maintaining a
  project portfolio, deciding which projects receive attention next, surfacing
  work blocked on user decisions or review, preparing a frozen daily execution
  plan for cron jobs, or reconciling planned work with actual outcomes.
metadata:
  author: symbolfarm
  version: "1"
  authored_by: agent
  status: draft
---

## Overview

The portfolio is a scheduling and attention layer above project-local work.
Each project remains authoritative for its own queue, task briefs, debriefs,
research notebook, Git history, and completion state. The portfolio answers:

- Which projects should receive attention now?
- Which filed tasks are safe to run unattended?
- What is blocked on a user decision, review, or external event?
- What bounded set of work should cron execute tomorrow?
- What actually happened compared with the frozen plan?

The central invariant is:

> The portfolio selects work; the project-level cycle defines and completes it.

Never copy full task descriptions or project completion state into the
portfolio. Reference project IDs and task IDs, then inspect the owning project
when planning or reconciling.

This skill assumes a dedicated portfolio repository, normally
`/workspace/project-portfolio`, containing:

```text
PORTFOLIO.md             human entry point and current attention summary
PROJECTS.json            machine-readable project registry and policy
DECISIONS.md             items requiring user decision or review
plans/YYYY-MM-DD.json    frozen inputs to daytime execution
reviews/YYYY-MM-DD.md    observed outcomes and planning lessons
scripts/validate_portfolio.py
```

Templates and the validator shipped with this skill live under `assets/` and
`scripts/`, relative to this `SKILL.md`.

---

## Boundary with project cycles

### Portfolio-cycle owns

- the set of projects participating in the portfolio;
- active/paused/candidate/completed status and relative attention;
- per-project automation policy and cross-project constraints;
- the user decision/review queue;
- dated daily execution plans and reviews.

### Task-cycle owns

- `.tasks/LOG.jsonl`, task files, task state, dependencies, and task IDs;
- acceptance criteria and implementation scope;
- task debriefs, completion housekeeping, and project commits.

### Research-cycle and research-notebook own

- project research direction, experiments, findings, and current beliefs;
- learning/planning/logging phases within one research repository;
- the notebook's correction and supersession discipline.

A portfolio record may say “run GNN-42 from `gnn-review`,” but it must not
repeat GNN-42's brief or claim that it is complete. Completion is established
from that project's task log, debrief, and Git history.

One work packet belongs to exactly one repository. Cross-repository changes are
separate project tasks ordered through explicit dependencies.

---

## Portfolio artifacts

### `PROJECTS.json`

The registry contains stable project identity and scheduling policy, not daily
task state. Use `assets/PROJECTS.json` as the template.

Important fields:

- `id`: stable short ID used by plans and decisions;
- `path`: absolute repository path;
- `status`: `active`, `paused`, `candidate`, `incubating`, or `completed`;
- `rank`: positive integer for active attention order, otherwise `null`;
- `attention`: `primary`, `secondary`, `maintenance`, `watch`, or `unranked`;
- `cycle`: `task`, `research`, or `none`;
- `skills`: ordered skill names to attach to work sessions;
- `automation.mode`: `cron_allowed`, `manual_only`, or `paused`;
- `automation.commit`: whether unattended work may commit locally;
- `automation.push`: false unless the user explicitly changes policy;
- `daily_task_limit`: maximum packets from this project in one daily plan.

Do not add `next_task`, `task_status`, or `last_commit` to the registry. Those
drift immediately and duplicate project truth.

### `DECISIONS.md`

This is the evening agenda. Keep two open queues:

- **Needs decision** — the user must choose direction or resolve ambiguity.
- **Needs review** — work exists and needs human inspection or acceptance.

Every item has an ID, project ID, related task where applicable, concise
question or review target, enough context to act, and the date raised. Ordinary
task dependencies stay in the project. Move resolved items to the recent
section with their outcome and date; Git history preserves older records.

### Daily plans

A daily plan is a bounded dispatch manifest created from
`assets/daily-plan-template.json`. A packet references one existing, unblocked,
filed task. It includes the target path, ordered skills, execution policy, and
stop condition. It also records the reviewed task file, task-file hash,
task-log-entry hash, and repository `HEAD`. These snapshots detect stale work
without copying task state into the portfolio. The packet does not reproduce
the task brief.

Plan states are `draft`, `frozen`, and `cancelled`. Once frozen and committed,
do not mutate the plan to record runtime status. Several cron jobs may read it
concurrently; immutable input avoids races. Record outcomes in the review.
A changed execution contract requires a new plan that explicitly supersedes
the old one; never silently amend a frozen contract.

### Daily reviews

A review records observed outcomes after execution: completed, blocked, failed,
deferred, or not dispatched. Verify every outcome against the project
repository rather than trusting an agent delivery message. Capture planning
lessons and new user-gated items for the next plan.

---

## Phase 1: bootstrap or refresh the registry

1. Confirm the portfolio repository path and inspect its Git status.
2. Discover candidate repositories under the agreed workspace root. Do not
   automatically activate every Git repository.
3. Inspect only enough to classify each candidate: Git state, `TASKS.md`, task
   log, notebook index, agent instructions, and automation suitability.
4. Add new entries as `candidate`, `rank: null`, `attention: unranked`, and
   `automation.mode: manual_only` unless the user activates them.
5. Assign stable IDs that remain valid if a directory is renamed.
6. Validate `PROJECTS.json` and commit the registry change.

Do not create missing task or notebook structures merely because a repository
was discovered. Their bootstrap is a separate project-local decision.

---

## Phase 2: evening planning

Evening planning is normally interactive. It turns project truth and user
judgment into tomorrow's frozen plan.

### Establish the delta

Start with the portfolio repository, then inspect active projects in rank order.
Prefer small deltas over full history replay:

- open tasks and blockers;
- recent debriefs and commits since the last review;
- dirty worktrees or existing `in_progress` tasks;
- research findings that change direction;
- unresolved `DECISIONS.md` entries.

Do not bulk-read every file in every repository. For a large portfolio, ask
read-only subagents for focused summaries, then verify selected tasks directly.

### Handle user-gated work

Walk open decisions and reviews first. Resolutions may change rank, invalidate
tasks, or make work executable. Record outcomes in `DECISIONS.md` and, where
needed, in the owning project.

Do not hide design questions inside daily packets. If a task needs a user
choice, exclude it from unattended work and file a decision item.

### Set attention

Agree on a small attention shape:

- one `primary` project receiving the largest share;
- zero or more `secondary` projects with bounded packets;
- `maintenance` only for concrete upkeep;
- `watch` projects observed but not scheduled.

Ranks must be unique among active projects. Respect task limits, energy/cost
windows, cross-project dependencies, and desired variety.

### Select packets

A task may enter a plan only when all are true:

- it exists in the owning project's task-cycle records;
- it is pending and dependencies are satisfied;
- acceptance criteria are concrete enough for cold unattended execution;
- declared `Touches` do not conflict with another concurrent packet;
- the project permits cron execution and local commits;
- the repository is clean, or explicitly sequenced after an earlier packet;
- no open user decision or review gates it.

Before freezing, record the registry revision, project `HEAD`, task-file path
and SHA-256, and the selected task-log-entry SHA-256. If a task has no stable
file or log entry, it is not ready for unattended execution.

Default to one task per packet and one packet per fresh agent session. A packet
may authorize a bounded list only for short sequential tasks with a clear stop
rule.

### Freeze and commit

Write `plans/YYYY-MM-DD.json`, run the validator, re-read every packet as its
implementer, and resolve surprises before setting `status` to `frozen`. Commit
the plan. Only a committed frozen plan may be dispatched.

Cron creation follows plan approval. Keep scheduler job IDs outside the
immutable plan; the packet ID is the stable join key.

---

## Phase 3: daytime execution

Each cron run starts cold and cannot ask questions. Its prompt must name one
packet, project path, task ID, ordered skills, and stop condition.

1. Set cron `workdir` to the target project.
2. Attach packet skills in order. Research execution usually loads
   `task-cycle`, `research-notebook`, then a project-specific skill. Load
   `research-cycle` only when the packet is itself a research-cycle phase.
3. Re-read project instructions, `TASKS.md`, task log, and named task.
4. Revalidate that the task is pending, unblocked, in scope, and safe on the
   current worktree.
5. Recompute the task and log-entry hashes. If they differ, skip and report;
   never choose a replacement task. A changed `HEAD` also fails closed unless
   direct inspection proves it consists only of an explicitly preceding packet
   from the same frozen plan and the task snapshots still match.
6. If anything needs user judgment, stop without guessing. Do not leave a task
   `in_progress` merely because it was inspected.
7. Execute, test, debrief, update project task records, and commit locally.
8. Never push unless both project policy and direct user instruction permit it.
9. Do not edit the portfolio repository from a project execution job.
10. Report packet ID, task ID, result, commits, verification, and any new
   decision/review item.

Stop and report on dirty user work, scope expansion beyond `Touches`, ambiguity,
or an acceptance criterion that cannot be satisfied. A clean partial state is
better than invented success.

---

## Phase 4: reconciliation

1. Read the frozen plan.
2. For every packet, inspect the owning project's task log, debrief, Git status,
   and commits. Treat cron output as a lead, not proof.
3. Write `reviews/YYYY-MM-DD.md` from `assets/review-template.md`.
4. Classify each packet with evidence.
5. Add user-gated items to `DECISIONS.md`.
6. Adjust attention only when outcomes justify it; do not churn rank because
   one task ran long.
7. Validate and commit the portfolio review separately from project commits.

The next evening plan consumes this review. Prefer committed artifacts over
carrying transient execution state in a chat.

---

## Parallelism and cron safety

- Parallelize across projects only when packets are independent and each writes
  to a different repository.
- Within one project, default to sequential runs. Task logs and the Git worktree
  serialize writes.
- Never let two jobs update portfolio registry, decisions, or the same review.
- Frozen plans are read-only during the work window.
- A dirty worktree, `in_progress` task, `Touches: unknown`, or ambiguous scope
  conflicts with all other work in that project.
- Stagger jobs to reduce provider, disk, and Git contention.
- Cron jobs commit but do not push by default.

---

## Validation

From the portfolio repository, run:

```bash
python3 scripts/validate_portfolio.py .
python3 -m unittest discover -s tests -v
```

Validation checks structure and policy, not whether a task is truly pending.
A valid frozen plan still requires direct project inspection before dispatch.

Verification checklist:

- [ ] portfolio Git status inspected first;
- [ ] no project task state duplicated into the registry;
- [ ] active ranks unique;
- [ ] packets name registered projects and matching paths;
- [ ] project paths resolve beneath the configured workspace root;
- [ ] packet task and log snapshots match the state reviewed by the planner;
- [ ] frozen packets target cron-allowed projects;
- [ ] no packet blocked on user input;
- [ ] daily limits respected;
- [ ] push disabled unless explicitly authorized;
- [ ] validator passes;
- [ ] portfolio and project changes committed independently.

---

## Common pitfalls

1. **Turning the portfolio into a second task queue.** Store references, not
   copied briefs or statuses.
2. **Letting cron choose strategy.** Strategy is fixed during evening planning;
   daytime jobs execute bounded packets.
3. **Scheduling draft work.** Only committed frozen plans are dispatchable.
4. **Making every project active.** Candidate and watch states protect focus.
5. **Hiding user decisions in task prose.** Promote them and exclude the task.
6. **Recording outcomes by mutating the plan.** Use a separate review.
7. **Running several jobs in one project worktree.** Sequence or isolate them.
8. **Trusting agent summaries.** Verify debriefs, task logs, tests, and commits.
9. **Pushing from unattended jobs.** Local commits are recoverable; publication
   remains separate.
10. **Loading portfolio-cycle in a project execution job.** Execution jobs need
    project cycle skills, not cross-project planning context.
