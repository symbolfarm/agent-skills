---
name: task-cycle
description: >-
  Manage the task lifecycle for this project. At the start of any work session,
  read TASKS.md in the repo root to orient yourself, then use this skill to
  decide whether work needs a durable task or just a small chore commit, start
  a task, complete it, and debrief. Covers: finding the next task, marking it
  in-progress, writing the debrief, updating LOG.jsonl, and committing the
  result.
metadata:
  author: symbolfarm
  version: "7"
  authored_by: user
  status: approved
---

## Overview

Tasks live in `.tasks/`. A task file exists means the task is incomplete.
A task file deleted (committed) means it is done. `LOG.jsonl` is the
append-only audit trail. `TASKS.md` (repo root) is the human- and
agent-facing entry point.

If the workspace holds more than one repo, read "Multi-project
workspaces" below *first* — "the repo root", "`.tasks/`", and "the
project" all mean *one specific repo*, and you need to know which.

Reading `TASKS.md` is orientation, not a requirement to file every
change as a durable task. Use the full task cycle for work that needs a
reviewable work order, handoff, acceptance criteria, or multi-session
audit trail. Small session-unblocking chores can be direct commits.

---

## Multi-project workspaces

A workspace may hold **several sibling repos**, each with its own
`.tasks/`, `TASKS.md`, and `LOG.jsonl`. The cycle is **per-repo**: every
step in this skill operates on *one* repo's `.tasks/`, and "the repo
root" always means the repo you are currently working in — never the
workspace directory above them (which has no queue of its own).

**Orient before you start.** At session start, `cd` into the target
repo and read *that* repo's `TASKS.md`. If the workspace has more than
one project, confirm which one this session is for before touching a
queue — the workspace root is a trap (no `TASKS.md`, no `.tasks/`).

**Per-project ID prefix.** Give each repo a short, distinct task-ID
prefix so IDs stay unambiguous when one repo's task or debrief
references another's. Jira-style `PROJ-N` reads well (e.g. `CR-1`,
`RB-7`). IDs are matched by exact string, so prefixes must not collide
across repos in the same workspace.

**One task, one repo.** A task belongs to **exactly one** repo; sibling
repos are *pinned dependencies* for it, not co-edited by it. If the work
needs a change in a sibling repo (a shared dependency, a harness, a
schema), that change is a **separate task filed in the sibling repo**
that lands first. Keep each repo's commit, LOG entry, and debrief
self-contained: a `commit` SHA is only meaningful within its own repo,
and each repo's branch / publication discipline stays independent. A
single git operation can't span two repos anyway — so neither should a
task.

**Cross-repo dependencies.** `blocked_by` holds task IDs *within the
same repo* only. To record a dependency on another repo's task, add a
`Depends-on (external):` line to the task header (e.g.
`Depends-on (external): retention-bench RB-7`) and explain the seam in
the body. These are resolved by hand — there is no automated cross-repo
blocking, so a dispatcher must check the named sibling task landed
before starting.

**Subagents and worktrees are per-repo.** A subagent handed a worktree
of one repo cannot touch a sibling. Split cross-repo work so each
subagent owns work in a single repo, and sequence across the repo
boundary (dependency repo first).

---

## Starting a task

Before starting, decide whether the work is large enough to deserve a
durable `.tasks/` entry. If it is a quick maintenance chore, use
"Small chores" below instead.

1. Read `TASKS.md` to understand the current state of the project. (In a
   multi-project workspace, first `cd` into the target repo — see
   "Multi-project workspaces" — and read *that* repo's `TASKS.md`.)
2. Read `.tasks/LOG.jsonl` to find the next unblocked task (status
   `pending`, no unresolved `blocked_by` entries).
3. Read the task file named in the log entry.
4. Update the log entry's status to `in_progress` (see "Editing
   LOG.jsonl" below).
5. Confirm the goal and acceptance criteria with the user if anything
   is ambiguous before starting work.

---

## Small chores

Do **not** file a task for every repo change. Prefer a direct
`chore:` commit when the work is all of:

- immediate maintenance needed to unblock the current session;
- mechanical or low-risk after inspection;
- small enough to complete and verify in one sitting;
- unlikely to need handoff, reviewable acceptance criteria, or a future
  audit trail beyond the commit itself.

Examples: fixing a stale path in `TASKS.md`, repairing a local dev
wrapper, formatting a touched file, or updating a small piece of
agent-facing documentation after reality has drifted.

If a small chore uncovers broader product/research work, finish or
revert the chore as appropriate, then file the broader work as a real
task. If you are already inside a task, handle eligible small chores as
"Drive-by cleanup landed" in the debrief rather than filing a second
task.

When in doubt, ask whether a future agent would need more than `git
show` to understand why the change happened. If yes, file a task; if no,
a direct chore commit is usually enough.

---

## Filing a new task

Tasks enter the queue via an explicit filing commit. This applies
whether the task came from initial planning, was surfaced mid-session,
or was triaged out of a debrief.

1. Write the task file using the template at
   `skills/task-cycle/assets/task-template.md`.
2. Append a `pending` entry to `LOG.jsonl` (see "Editing LOG.jsonl").
3. Commit the new task file + LOG entry together as
   `chore: file <task-id> — <one-line summary>`.
4. Only flip the LOG entry to `in_progress` *after* the filing commit
   has landed (and only if you're starting work on it now).

**Why a separate commit?** It keeps the audit trail clean: the
filing commit explains why the task exists; the work commit explains
what was done. Bundling them obscures both. It also makes "what's
queued?" answerable from `git log --grep='chore: file'` alone.

Bulk-filing several tasks at once (e.g. M1-M7 at project start) is
fine in a single commit; one commit per *batch of related tasks*,
not one commit per task.

### Re-read pass before starting work

After writing a brief, you are in "writer" mode. Before starting the
work, re-read it once in "implementer" mode — *what would surprise
the person about to build this? What did I punt on?* The frame
change is what makes the pass useful; a generic "quality review" is
performative.

This pass is **not** mandatory for every task. Do it when **any** of:

- First slice of a new phase, subsystem, or first-of-kind work
- Brief contains "author's choice", "implementer to decide", or
  other punted decisions
- Security-visible surface area (permissions, scopes, user data,
  network, disk writes)
- Introduces a new user-facing surface (new pane, mode, tab — not
  "edit an existing component")
- Touches three or more subsystems (e.g. Rust + IPC + UI + tests)
- Swaps or renames a dependency, SDK, protocol, or env-var contract
  that the test suite **mocks, shadows, or fixtures against** (the
  scaffold usually impersonates the exact surface you're changing, so
  the test impact is larger and less visible than the source change)

If none apply, skip — small bug fixes and refactors stay light.

Common things this pass catches: omissions in the UI refresh /
event-wiring story; security-visible fields displayed without enough
context for the reviewer; decisions silently punted to the
implementer; collision/edge cases on the unhappy path; the LLM-facing
return value of a new tool; test-infra that *impersonates the thing
being changed* — a swapped or renamed dependency/SDK/protocol usually
means a fake shim, fixtures, and env-var plumbing all need porting in
lockstep, so grep the old name across `tests/` and fixtures and size
those hits as first-class work, not a footnote.

If the pass surfaces changes, amend the brief in a **separate
follow-up commit** (`chore: refine <task-id> brief — <what>`) rather
than rewriting the filing commit. The separation keeps the audit
trail honest: filing commit = initial intent, refine commit = what
we learned by re-reading.

Note: this does not replace the debrief. The re-read pass catches
issues *before* contact with reality; the debrief catches what was
wrong with the brief *after*. Different failure modes.

---

## Completing a task

Run these steps after the work is done and committed.

### 1. Write the debrief

Create `.tasks/debriefs/<task-id>-<slug>.md` using the debrief template
in `skills/task-cycle/assets/debrief-template.md` — use the **same
`<task-id>-<slug>`** as the task file (e.g. task `C11-incontext-validation-sut.md`
→ debrief `C11-incontext-validation-sut.md`), so debrief filenames are
scannable and mirror their task. Cover:

- What was shipped (brief, factual)
- What was descoped or deferred, and why
- **Design decisions made in-flight** — any choice that deviated
  from the brief, wasn't pre-specified, or involves a non-obvious
  trade-off, even if small/reversible. Surface them so the user
  can review in one place; don't bury them in the prose.
- Anything surprising or non-obvious encountered
- Candidate new tasks surfaced during the work

### 2. Update LOG.jsonl

Update the task's existing line so it ends up looking like:

```json
{"id":"<task-id>","status":"completed","priority":"<p>","blocked_by":[],"task_file":"<filename>","commit":"<sha>","created_at":"<iso8601>","completed_at":"<iso8601>"}
```

Set `commit` to the SHA of the commit that delivered the work. See
"Editing LOG.jsonl" below for the recommended mechanic.

### 3. Delete the task file

```bash
git rm .tasks/<task-file>
```

The file persists in git history — this is intentional.

### 4. Commit the housekeeping

Stage and commit the debrief, the updated LOG.jsonl, and the deleted
task file together:

```
chore: complete task <task-id> — <one-line summary>
```

### 5. Triage candidate tasks

For each candidate surfaced during the work, pick one of three paths
**before** asking the user. Don't route every candidate through a
user check-in.

- **Drive-by** — mechanical, under ~5 minutes, obviously safe,
  correctness self-evident from a glance. Just do it as a follow-up
  commit in the same session. Note it under a "Drive-by cleanup"
  bullet in the debrief; don't file a task.
- **Real task** — needs a decision, spans multiple files
  non-trivially, risky enough to want pre-merge review, or might
  take more than one sitting. File it: create a task file using
  `skills/task-cycle/assets/task-template.md`, append a `pending`
  entry to LOG.jsonl.
- **Drop** — sounded interesting in the moment but on second look
  adds no value, or duplicates existing work. Don't mention.

If a candidate doesn't clearly fit one bucket, default to **real
task** and let the user re-triage. Filing is reversible; landing
unreviewed cleanup isn't.

Surface to the user only the *real tasks* you've decided to file,
plus a one-line note for any drive-bys that landed. Don't enumerate
candidates individually for approval.

---

## Editing LOG.jsonl

Hand-editing JSONL with the `Edit` tool is awkward — lines are
similar enough that finding a unique `old_string` is fragile.
**Strongly prefer `jq`** for in-place updates.

To update fields on an existing entry:

```bash
jq -c '(select(.id=="<task-id>") | .status) = "<new-status>" | (select(.id=="<task-id>") | .commit) = "<sha>"' \
  .tasks/LOG.jsonl > .tasks/LOG.jsonl.tmp && mv .tasks/LOG.jsonl.tmp .tasks/LOG.jsonl
```

Or, more readably, use a single `if` to set multiple fields at once:

```bash
jq -c 'if .id=="<task-id>" then .status="completed" | .commit="<sha>" | .completed_at="<iso8601>" else . end' \
  .tasks/LOG.jsonl > .tasks/LOG.jsonl.tmp && mv .tasks/LOG.jsonl.tmp .tasks/LOG.jsonl
```

To append a new entry (e.g. when surfacing a candidate task), just
append a single-line JSON object with `>>`. Re-running the file
through `jq -c .` afterwards is a cheap sanity check that every line
parses.

If `jq` isn't available for some reason, rewriting the whole file
with `Write` is acceptable — it's a small file.

---

## Splitting a task

When an in-flight task turns out to be too large, split it into
subtasks rather than letting it sprawl. Convention:

1. Create one new task file per subtask (`<original-id>a`, `<original-id>b`, …).
   Append a `pending` log entry for each, with `blocked_by` reflecting
   any sequential dependencies.
2. Mark the parent's log entry as `superseded`, set
   `superseded_by` to the array of new task IDs, and stamp
   `completed_at` with the split timestamp. Do **not** delete the
   parent task file as part of the split commit — instead, `git rm`
   it the same way as a completed task, since the file's purpose
   (being the open work order) is over.
3. Write a short debrief at `.tasks/debriefs/<parent-id>-<slug>.md` noting
   the split rationale and pointing to the children. This keeps the
   audit trail uniform: every removed task file has a debrief.
4. Commit as `chore: split <parent-id> into <child-ids>`.

Rationale: `superseded` distinguishes "this work didn't happen as
specified" from `completed` ("this work shipped"), so future readers
of LOG.jsonl can reconstruct what actually happened.

---

## Context management

The cycle is designed around a simple goal: each task fits in one
agent's context lifetime, so no agent has to compact or clear
mid-task. The debrief file is the handoff artifact — written
once, readable cold.

**Sizing.** Aim for tasks small enough that you don't need to
`/compact` during them. Rough heuristic: a task should fit in a
session's worth of attention. If you find yourself wanting to
compact, you're probably oversized — split (see "Splitting a
task" above) and `/clear` between subtasks.

**Between tasks.** When the next task is unrelated to the one
you just finished, prefer `/clear` over carrying the full
conversation forward. The debrief is the persistent state; the
conversation is not. `TASKS.md` + LOG.jsonl + the debrief is
all the next agent needs to start cold.

**Within a task.** For read-heavy work that produces a small
answer — codebase exploration, multi-file searches, "find all
callers of X" — spawn a read-only search subagent rather than burning
the parent's context on raw tool output. The parent steers; the
subagent reports ~200 words.

**Compacting as a smell.** If a task needs `/compact` mid-flight,
the task was too big or the agent is over-narrating. Compaction
loses fidelity; splitting preserves it.

---

## Relationship to harness Task tools

The harness exposes its own `TaskCreate` / `TaskUpdate` / `TaskList`
tools. Those manage **in-session** todo lists — ephemeral checklists
that disappear when the conversation ends. This skill manages
**cross-session** durable tasks tracked in git.

They are complementary, not competing:

- Use `.tasks/` files for work that may take multiple sessions, that
  you want the user to review, or that should be part of the project's
  audit trail.
- Use harness `TaskCreate` for within-session implementation
  checklists — the steps you'd otherwise hold in your head while
  executing a single `.tasks/` task.

If you choose not to use the harness Task tools for a given session,
ignore the harness's reminder to do so. Splitting a `.tasks/` task
into subtasks is a `.tasks/` operation (see "Splitting a task"
above), not a `TaskCreate` operation.

---

## Delegating to subagents

When running multiple `.tasks/` items in one session via subagents
(e.g. clearing a queue), prefer **sequential** dispatch by default
— LOG.jsonl and the shared git worktree both serialise writes, and
overlapping `Touches` (see "Parallel-safe scheduling" below) produce
silent conflicts. Parallel dispatch only pays off when (a) tasks are
long enough that wall-clock matters and (b) you've isolated the
worktree (e.g. `git worktree add` per subagent) so the LOG.jsonl
write step doesn't race.

Whether sequential or parallel, give each subagent prompt:

- **A scope cap** — either a single named task, or "up to N tasks
  from this list, stop when you hit one that needs design input."
- **A budget hint** — e.g. "stop after ~K tool calls and report
  remaining queue." Subagents can't introspect token usage but can
  count their own tool calls as a proxy.
- **A stop-and-report rule** for ambiguity, design questions, or
  `Touches` mismatches — better to surface than to guess.
- **A short-form report contract** — what shipped, commit SHAs,
  design decisions made (even reversible ones), and what's left in
  the queue. The parent uses this to decide whether to continue.

The dispatching agent verifies LOG.jsonl, debriefs, and commits
landed as claimed before moving on (subagent reports describe
intent, not necessarily reality).

---

## Parallel-safe scheduling

Tasks declare `Touches:` in their header — a best-guess set of
files or globs the work will modify. The field has two uses:

- **Conflict detection (sequential runs).** Before starting a task,
  scan other `in_progress` or recently-touched task entries for
  overlapping `Touches`. Overlap is a signal to merge or sequence
  the work, not an error.
- **Parallel scheduling (delegated runs).** A loop dispatching tasks
  to multiple subagents may co-run two tasks only if their
  `blocked_by` is satisfied **and** their `Touches` sets are
  disjoint. Tasks marked `Touches: unknown` — or tasks predating
  this field that have no `Touches:` line at all — are treated as
  conflicting with everything and run sequentially.

`Touches` is a hint, not a contract. If a subagent discovers
mid-task that it needs to modify a file outside its declared set,
it should stop, report the mismatch, and let the scheduler
re-evaluate rather than silently expanding scope.

---

## Sync check

If you suspect task files and LOG.jsonl have drifted out of sync, run:

```bash
# Files present but not in log (orphaned task files). Match on the
# whole filename against the log's `task_file` field — this is
# format-agnostic, so it works for both legacy IDs (C11-slug.md) and
# Jira-style prefixes (CR-1-slug.md) without parsing the id out of the
# name (a Jira `<prefix>-<n>-<slug>` name has no single delimiter that
# separates id from slug).
for f in .tasks/*.md; do
  base=$(basename "$f")
  grep -q "\"task_file\":\"$base\"" .tasks/LOG.jsonl || echo "ORPHAN: $f"
done

# Log entries open (pending / in_progress) but file missing (lost task files)
jq -rc 'select(.status=="pending" or .status=="in_progress") | .task_file' .tasks/LOG.jsonl | while read -r file; do
  [ -f ".tasks/$file" ] || echo "MISSING FILE: $file"
done
```

Report any discrepancies before proceeding.

---

## LOG.jsonl field reference

| Field | Description |
|---|---|
| `id` | Unique task ID, e.g. `task-007` |
| `status` | `pending` / `in_progress` / `completed` / `superseded` |
| `priority` | `high` / `medium` / `low` |
| `blocked_by` | Array of task IDs that must complete first (empty `[]` if none) |
| `task_file` | Filename within `.tasks/`, e.g. `task-007-rhai-engine.md` |
| `commit` | Git SHA of the completing commit (null until completed; null for superseded) |
| `created_at` | ISO 8601 timestamp |
| `completed_at` | ISO 8601 timestamp (null until completed; for superseded entries, the split timestamp) |
| `superseded_by` | Array of task IDs that replace this one (only present on `superseded` entries) |
