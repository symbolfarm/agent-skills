---
name: work-cycle
description: >-
  Execute one durable work item: claim and deliver a portfolio goal, or start,
  complete, and debrief a repository task. Use when asked to take the next goal
  or task, continue in-flight work, file implementation tasks, or close out a
  completed item. Works with a portfolio when one is reachable and with a single
  repository when it is not.
license: MIT
metadata:
  author: Symbol Farm
  version: "9"
  category: productivity
  tags: portfolio, goals, tasks, execution, work-cycle
---

# Work cycle

One execution skill, two item types:

- A **goal** states an outcome. The portfolio owns it, and the user creates it in
  a review. A goal's `Done when` is the contract; the agent decides the
  implementation unless the goal carries optional `Implementation opinions`.
- A **task** states implementation. One repository owns it, and an agent may file
  it while executing a goal or working directly in that repository. Its brief is
  a handoff artifact with acceptance criteria.

This is an outcome/implementation distinction, not a size distinction. A small
handoff may need a task; a substantial outcome can remain one goal. The split is
in **creation**, not execution, so both types use this cycle.

Execute at most one selected item per run by default. A caller may declare a
larger **run budget measured in fully closed items**; when it does, repeat this
cycle from selection only after the current item is committed and its lifecycle
is closed. Never carry one item's open lifecycle state or unverified assumptions
into the next: reread the durable queue, reset the ephemeral checklist, and use a
fresh sub-context when the runtime supports one. A caller may also declare a
lower budget for a fallback model, or a wind-down condition. Such a rule is
valid only when the caller names stable primary/fallback identifiers and an
observable runtime source. Inspect the current execution's model/provider
metadata before the first item and before every later selection; configured
defaults do not prove the model actually running. Corroborate with the durable
scheduler execution record when available. If identity cannot be established,
use the conservative fallback budget and say so. Demoting a user-blocked goal
remains an exception even under the
default one-item budget, so the run may take the next eligible goal rather than
starving the queue. Commit at natural boundaries. Git is the record; task
debriefs preserve only what Git cannot.

## 1. Establish the operating mode

### Portfolio mode

Use portfolio mode when a portfolio repository is reachable. It normally holds
`GOALS.md`, `PROJECTS.json`, `CALIBRATION.md`, `LOCKING.md`, and `log/`.
`OWNER.md`, when present, is standing prose rather than a second executable
checklist. Point the skill at the portfolio's actual location; do not assume a
fixed path.

Read, before changing anything:

1. `GOALS.md`;
2. `PROJECTS.json`;
3. `CALIBRATION.md`;
4. `LOCKING.md`;
5. the selected project's `TASKS.md`, `AGENTS.md`, or `CLAUDE.md`, when present.

The portfolio queue is the sole source of **strategic priority**. Position is
priority. A caller may supply an explicit lane allocation or ordered eligibility
pass—for example, product goals first with research as fallback. That is routing,
not a second strategic rank: state it explicitly and preserve queue order within
each eligible set. With no caller allocation, scan the canonical queue directly.
Do not invent a lane policy, substitute unrelated work, or enter a project not
named by the selected goal.

### Repository-only mode

A sandbox may expose only one repository and no portfolio. That is a supported
mode, not an error. Read that repository's `TASKS.md`, `.tasks/LOG.jsonl`, and
its agent instructions. Select the next pending, unblocked agent-assigned task,
or the named task if the caller supplied one.

With no reachable `CALIBRATION.md`, treat every reversible decision as
**report**. This deliberately produces a noisier record than portfolio mode; do
not copy a private calibration ledger into public repositories to avoid that
cost.

### Multi-repository workspaces

Every task belongs to exactly one repository. A sibling repository is a pinned
external dependency, not a second edit target. If work needs a sibling change,
file and land a separate task there first. Record it as `Depends-on (external):
<repo> <task-id>`; `blocked_by` contains IDs from the same repository only.

Do not touch an unrelated dirty or locked repository. A worktree is clean only
when `git status --porcelain` is empty. Unavailability is per repository and
skips only that repository's items — see **Repository availability** below.

## 2. Select one item

### Selecting a goal

Take the highest-priority eligible goal under the explicit selection contract:

1. A claim by this agent with resumable progress comes first; reacquire the lock
   and resume rather than skipping to new work.
2. Otherwise take the first unclaimed, unblocked goal.
3. A goal claimed by another agent with a live lock is unavailable; continue
   down the queue.

The goal's project must be `active` in `PROJECTS.json` with non-empty
`agent_may`. A mismatch is a no-op worth reporting; do not work around it.
Anything in a `strict`-tier project stops for review—no provisional defaults.

A goal's explicit `Requires` overrides the project's default requirements,
including with an empty value. Verify each declared capability before claiming.
If one is absent, skip the goal without moving or blocking it, and report the
missing capability. Explicit caller allocation, capability, assignee/gate state,
claims, and repository availability are the only reasons selection may differ
from the raw queue head. Difficulty, length, and undeclared preference are never
skips.

Items with `assignee: <person>` are not agent work. `Requires: computer` means
raise the item in the interactive review; without it, the recurring brief may
route it to the user. Do not execute either kind on the user's behalf.

A goal may name existing repository tasks with `Implements`. Treat those IDs as
explicit implementation links, not copied task state: inspect each named task in
the owning repository before editing. A pending linked task is the implementation
work order; after claiming the goal, transition that existing task to
`in_progress`, then lock and execute it. Resume an `in_progress` linked task using
the interrupted-task rules. If it is completed, verify its evidence against the
goal rather than recreating it. Never file a duplicate task around an
`Implements` link. Close the linked task lifecycle before closing the portfolio
goal.

A goal may declare `Blocks:`, naming the goals or repository tasks that cannot
proceed until it lands. It is a **derived-view field, not a second queue**:
position in `GOALS.md` remains priority, and `Blocks:` only lets the brief and
review say *why* an item sits where it does. Do not re-rank on it, and do not
select a goal because it gates others. It is reporting metadata, not selection
input. (Set in `portfolio-cycle` when the goal is filed; surfaced by the merged
view and `portfolio-brief`.)

### Repository availability

A repository is available when its worktree is clean and no other agent holds a
live `.tasks/.lock`. Check the item's repository before claiming it;
`scripts/repo_availability.py` in this repository reports one repository's state,
and its `first_available` applies the rule to a queue in order.

**An unavailable repository costs its own items, never the run.** Skip every item
belonging to it — without claiming, moving, or blocking those items — continue
down the queue, and take the first item whose repository is available. A run that
stops because one repository was dirty has converted one stalled item into a
stalled day.

**Do not clear the obstruction to make an item runnable.** Uncommitted work is
its author's: never `stash`, `clean`, `reset`, or commit it, and never guess at
what an untracked file was for. Replacing an *expired* lock is the single
exception, and §3 covers it.

**File the anomaly, then keep working.** Record each unavailable repository once
per run as an item in the same queue substrate, carrying an `*Anomaly:* <repo> —
<what was found>` line: the porcelain paths, or the lock's holder and expiry.
Say what would clear it, and mark it `assignee: <user>` when the residue is
theirs to rule on — uncommitted work an agent must not guess at usually is. The
`*Anomaly:*` line is what lets a report distinguish an obstruction the lane
routed around from work someone chose to queue; without it a skipped repository
reads as a healthy backlog. In repository-only mode the unavailable repository
may be the only one, leaving nowhere to file: report it in the close-out and end
the run as a no-op.

### Selecting a task

From `.tasks/LOG.jsonl`, take the first eligible entry whose status is `pending`,
whose `blocked_by` entries are resolved, and whose assignee permits this agent.
Read the referenced task file before marking it in progress. If the caller names
a task, verify those same gates rather than silently taking a different one.

`LOG.jsonl` is a current queue encoded as one JSON object per line, not an
append-only event stream. Keep exactly one record per task ID: append it when the
task is filed, then update that record in place for `in_progress`, `completed`,
or `superseded`. Git history, work commits, and debriefs are the immutable audit
trail. Task order in the file is selection order; do not add a competing
high/medium/low priority field.

If task files and the log may have drifted, verify both directions:

- every `.tasks/*.md` work order has a matching `task_file` entry;
- every `pending` or `in_progress` log entry has its work-order file.

Report discrepancies before executing the task.

### Reconstructing interrupted work

For a claimed goal:

- claimed by this agent and lock live: resume;
- claimed by this agent, lock released, progress recorded: confirm a clean
  worktree, reacquire, and resume;
- claimed by another agent and lock live: leave it;
- claim older than 24 hours and lock expired: inspect progress and project
  commits since the claim, re-claim explicitly, and log the takeover;
- claim with no commits and no progress: re-claim and start fresh.

Reconstruct from `Done when`, not from a guessed prior plan. If restarting is
cheaper than reconstructing, restart and say so in the close-out.

For an `in_progress` task, read its brief, debrief candidates, and commits since
its start. The task file remains the work order until completion or
supersession.

## 3. Claim, then lock

### Goal claim

Add `Claimed: <agent>, <ISO-8601 timestamp>` to the goal and commit the portfolio
change **before project work**. Claiming is a commit so concurrent agents collide
visibly instead of duplicating work.

### Task start

A task must already have a filing commit. Update its existing JSONL entry from
`pending` to `in_progress` before implementation. Do not bundle initial filing
and implementation into one commit.

### Repository lock

After the claim or task-state transition, acquire `.tasks/.lock` atomically per
`LOCKING.md`, normally with `O_CREAT | O_EXCL`. The lock records holder, item,
acquired time, and expiry. Default TTL is two hours, adjusted to the work.

- Live lock held by another agent: do not wait or edit. Release the claim, file
  the anomaly, and take the next item whose repository is available — the lock
  blocks that repository, not the run.
- Expired lock: record that it is stale, replace it atomically, and continue.
- Release the lock after the final project commit and on every exit path.

Order is always item claim/state transition, then repository lock, then edit.

## 4. Decide whether to file tasks

A task brief is a handoff artifact. File one when work goes to another agent or
future session, needs review before landing, or needs a durable implementation
work order. Work performed now by the agent already holding context can be a
chore/docs commit, even when substantial.

| Situation | Record |
|---|---|
| Do it now; no decision worth preserving | direct `chore:` / `docs:` commit |
| Do it now; non-obvious choice | direct commit with a short `Decisions:` body |
| Handoff, future session, or review gate | task file + JSONL entry + debrief |

A goal may generate tasks, but it does not have to. Do not mechanically wrap a
goal in a duplicate task.

### Filing a task

1. Create `.tasks/<id>-<slug>.md` from `assets/task-template.md`.
2. Append one `pending` object to `.tasks/LOG.jsonl`.
3. Commit both as `chore: file <id> — <summary>`.
4. Re-read the brief in implementer mode when it introduces a subsystem or
   user-facing/security-visible surface, punts decisions, spans three or more
   subsystems, or changes a mocked protocol/dependency. Commit refinements
   separately.
5. Only then set it `in_progress` if starting it now.

Use distinct per-repository ID prefixes. `Touches` is a scheduling hint: an item
with missing/unknown touches conflicts with everything; if work expands beyond
its declaration, stop and re-evaluate rather than silently widening a delegated
scope.

## 5. Execute and verify

Follow the repository's conventions and the selected item's contract. Optional
`Implementation opinions` on a goal are instructions, not mere context. In
their absence, file and implement tasks freely within the outcome.

Implementation opinions constrain this one outcome—for example, a required
interface or an approach the user does not want. They do not set how a class of
decision is handled. `CALIBRATION.md` governs decision classes everywhere, so do
not encode per-goal `ask`, `report`, or `auto` involvement levels in an
implementation-opinions line.

Run the relevant tests and exercise the artifact. A successful write or command
is not completion: inspect the changed target, test the user-visible path, and
check every `Done when` or acceptance criterion. For an external state change,
read the exact target back before claiming success.

Commit at natural boundaries. Small commits make interrupted work recoverable.
Do not push unless the caller explicitly assigns publication; scheduled setups
may reserve pushing for a host-side pusher.

### Decisions

Use the reachable calibration ledger:

| Level | Behaviour |
|---|---|
| `auto` | Decide and proceed; do not log the decision. |
| `report` | Decide and proceed; record choice and reasoning. |
| `ask` | Stop; do not decide. Record what is needed. |

An unknown class is `unclassified` at report level. Do not mint a new class.
With no ledger, all reversible choices are report-level.

Reversible means a Git operation undoes it, including an ordinary push or
deployment under an experimental disclaimer. Never default, regardless of the
ledger, on package-registry publication, spending, third-party contact,
publishing under the user's name, secrets, destruction without another copy,
anything in a strict project, or what the research record says we believe.

Make provenance visible in durable prose: distinguish measured facts, inferences
(`X, so Y`), and assumptions. When a surprising number does not fit the story,
re-measure and re-derive the chain rather than polishing the prose.

## 6. Research findings during execution

A completed implementation task can produce a finding. Before closing it, ask:
*did this change what we believe, rule something out, or develop the theory?*

- If no—chores, refactors, harness wiring—do not manufacture notebook work.
- If yes, update the research notebook before final housekeeping: settle the
  experiment note, propagate the result into live notes using the notebook's
  correction/supersession discipline, append today's lab log, and update
  `INDEX.md`. Findings remain provisional wherever belief change requires the
  user to ratify them.

This is the former research workflow's logging phase. `research-notebook`
defines the artifact; this skill closes execution back into it.

## 7. Complete, split, block, or pause

### Complete a goal

1. Release the project lock after the final project commit.
2. Move the goal to `Completed`, replacing the claim with a dated completion
   record, project commit SHAs, and a `Try it` command/path/link.
3. Append the portfolio log entry described below.
4. Commit portfolio changes separately from project work.
5. Re-read the goal from `GOALS.md` and confirm it is no longer executable queue
   work; then verify the portfolio worktree is clean. A project commit plus an
   uncommitted portfolio close-out is **not** a completed goal.
6. When the caller supplied a multi-item budget, decrement that budget only
   after steps 1–5 pass. If the lifecycle record or portfolio commit is missing,
   stop the run without selecting another item.

If completion archives the project, clears `agent_may`, or otherwise removes
push authority, first verify the project branch is at remote parity. If commits
are still ahead, leave the project active and the goal in flight with `Progress:
awaiting publish, then verify and archive`. When deployment is part of `Done
when`, verify the deployed artifact too.

### Complete a task

After the work commit:

1. Write `.tasks/debriefs/<same-id-and-slug>.md` from
   `assets/debrief-template.md` for a future agent. Do not restate the diff.
   Record in-flight design decisions, descoped work, hidden constraints, and
   triaged follow-ups.
2. Update the existing JSONL entry to `completed`, setting the work commit and
   completion timestamp.
3. Delete the task file; Git history preserves it.
4. Include the debrief, JSONL update, task deletion, and any finding distill in
   `chore: complete task <id> — <summary>`.

Triage follow-ups before surfacing them: do mechanical five-minute cleanup now;
file non-trivial or review-worthy follow-ups as tasks; silently drop duplicates
or valueless ideas.

### Split an oversized task

File child tasks (`<id>a`, `<id>b`, …), with dependency order. Mark the parent
`superseded`, set `superseded_by`, stamp its completion time, remove its work
order, and write a short parent debrief explaining the split. Commit the split
as one lifecycle change.

### User-blocked goal

A goal no agent can advance must not remain claimed at the queue head:

1. remove its claim;
2. move it to `Blocked` with what is needed, who owns it, and the date;
3. add the established unblock to the same merged item substrate with
   `assignee: <user>`, naming the goal it blocks and `Requires: computer` when
   appropriate;
4. commit and take the next eligible goal in the same run.

A later goal gated by the current result needs the same three visible records:
completion note, blocked line on that later goal, and assignee-marked unblock
item. Adding that item is transcription of a requirement created by approved
work, not permission to invent a new user outcome. Restoring a
blocked goal to the queue is a review-time priority decision.

A missing machine capability is not a user block. Leave that goal in place and
unclaimed.

### Partial result

When real work is resumable by an agent, keep the claim only if it will resume
soon, add one `Progress` line naming what landed and the exact next step, release
the lock, and commit. If the remainder needs the user, demote it instead.

Stop rather than expanding silently when the item is much larger than one run,
its contract is genuinely ambiguous, an ask/irreversible decision is required,
or the queue and registry disagree.

### Run exit gate

Before returning from any portfolio-mode run — including budget exhaustion,
fallback wind-down, blocking, partial work, and tool/context pressure — verify
that every item touched in the run has one durable terminal state: completed,
visibly blocked, explicitly resumable with `Progress`, or released as a no-op.
For every completed goal, verify the project commit, portfolio log entry,
`GOALS.md` lifecycle move, and separate portfolio commit all exist, and verify
the affected worktrees are clean. If they do not, finish that close-out before
writing the final response; never report the residue as a later brief's problem.

**Make this an assertion, not a remembered checklist item.** Resolve
`scripts/lifecycle_guard.py` relative to this skill's directory and run it over
every item touched in the run immediately before returning:

```bash
python3 <work-cycle-skill>/scripts/lifecycle_guard.py goal-exit \
  <portfolio>/GOALS.md G-002 G-014
python3 <work-cycle-skill>/scripts/lifecycle_guard.py task-exit \
  <repository>/.tasks/LOG.jsonl EX-4
```

Use the goal command for portfolio goals and the task command for repository
tasks; split calls by owning ledger. A non-zero exit is a **refusal to end the
run**: it names each goal still carrying an unmatched claim without a
`Progress` record, or each task still `in_progress`. Finish the lifecycle
close-out and rerun the guard. A goal in `Completed` or `Blocked`, a claimed goal
with explicit `Progress`, and a task in a terminal state pass. The guard never
releases or rewrites a claim.

## 8. Portfolio log and handoff

For a portfolio goal, append to `log/YYYY-MM-DD.md`:

```markdown
## G-002 `example-tool` — closeout pass

**Result:** done / partial / no-op / blocked
**Commits:** 4 in example-tool
**Try it:** `command`, path, or URL — the quickest useful check.

**Decisions**
- *api-shape (report):* chose X because Y.
- *unclassified (report):* chose the layout for Z because Y.

**Weakest point:** the least-tested path or load-bearing assumption.
```

`Try it` and `Weakest point` are required when there is an artifact or a real
verification ceiling. Do not log `auto` decisions. A repository-only task uses
its debrief plus the session report rather than inventing a portfolio log.

## Context and delegation

Aim for one selected item at a time. Under a caller-declared multi-item budget,
create a cold-start boundary between items: close all durable state, discard the
item-specific plan, reread selection sources, and prefer a fresh sub-context
when the runtime supports one. This is a lifecycle/context hygiene boundary, not
a claim that every scheduler invocation literally creates a new conversation.
If compaction looks necessary inside an item, split the task; debriefs and
commits preserve fidelity better than a compressed conversation. For read-heavy
exploration, a read-only subagent may return a short synthesis. Sequential
delegation is the default because the worktree and JSONL log serialize writes;
parallelize only with isolated worktrees and disjoint `Touches`.

A delegated prompt must name one item, a scope cap, a tool-call budget hint, a
stop rule for ambiguity or touch expansion, and a report contract covering
commits, decisions, and remaining work. Verify the repository state rather than
trusting a subagent's report.

Harness task-list tools are ephemeral session checklists. `.tasks/` is the
cross-session Git record. They complement one another.

## Pitfalls

1. Working before claiming the goal or transitioning the task.
2. Treating goals and tasks as different sizes instead of outcome vs
   implementation.
3. Duplicating every goal as a task or executing an unreviewed outcome as if it
   were implementation detail.
4. Re-ranking a portfolio queue or substituting unrelated work.
5. Touching a dirty, locked, unrelated, or strict repository — or clearing
   someone's residue so an item becomes runnable.
6. Ending the run because one repository was unavailable, instead of skipping
   its items, filing the anomaly, and taking the next eligible item.
7. Blocking on a reversible decision—or defaulting an irreversible one.
8. Copying a private calibration ledger into a sandboxed/public repository.
9. Logging `auto` decisions or inventing calibration classes.
10. Leaving a user-blocked goal claimed at the head.
11. Describing an artifact without handing over the way to try it.
12. Letting a task debrief duplicate Git instead of recording what Git cannot.
13. Distilling plumbing into the research notebook, or failing to distill a real
    finding.

## Checklist

- [ ] Selected the first eligible item from the correct source.
- [ ] Portfolio project is active, permitted, and capability-compatible.
- [ ] Claim/state transition committed before project edits.
- [ ] Repository was available (clean, unlocked) and atomically locked; lock
      released on every exit.
- [ ] Any unavailable repository cost only its own items and was filed as an
      anomaly item.
- [ ] No unrelated repository or irreversible action was touched.
- [ ] Optional implementation opinions and the item contract were followed.
- [ ] Relevant tests and the actual artifact were exercised.
- [ ] Findings were distilled only when work changed understanding.
- [ ] Decisions follow the ledger, or all use report when no ledger is reachable.
- [ ] Goal log includes `Try it` and `Weakest point`; task close-out includes its
      debrief and JSONL update.
- [ ] Project and portfolio changes are separate commits.
- [ ] The item is complete, explicitly resumable, superseded, or visibly blocked.
- [ ] Run exit gate passed: every touched item's lifecycle is durable and each
      affected worktree was rechecked clean; `lifecycle_guard.py` passed for
      every touched goal and task.
