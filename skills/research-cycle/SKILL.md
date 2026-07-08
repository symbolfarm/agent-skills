---
name: research-cycle
description: >-
  Drive the research workflow for a project that keeps a research
  notebook. Three phases: learning (catch the user up on the current
  state of theory, experiments, and implementation, and set the next
  direction), planning (break an agreed direction into filed
  task-cycle tasks), and logging (close out an experiment or finding
  into the notebook). Use when the user asks to get up to speed, review
  the state of play, decide what's next, plan an experiment, or wrap up
  a finding. Builds on the research-notebook skill (the artifact) and
  task-cycle (execution).
metadata:
  author: symbolfarm
  version: "1"
  authored_by: agent
  status: draft
---

## Overview

Research work loops through three phases:

```
learning ──► planning ──► execution ──► logging ──┐
   ▲          (filing      (task-cycle)           │
   └──────────  tasks)  ◄─────────────────────────┘
```

- **Learning** — sync the *human's* understanding with the project's
  current state, and end with a direction.
- **Planning** — turn the direction into a work breakdown, filed as
  task-cycle tasks.
- **Logging** — when an experiment concludes or a finding lands,
  distill it into the notebook so the next learning session starts
  from truth.

Execution itself belongs to the `task-cycle` skill; every artifact
this skill writes follows the `research-notebook` skill's conventions
(layout, statuses, correction discipline). Read both before acting.

The phases are independently invocable — "catch me up" is a learning
session with no obligation to plan; a finding can be logged without a
planning session following it. But each phase assumes the previous
one's output exists somewhere: don't plan without a stated direction,
don't start experiment tasks without a hypothesis written down.

Like its companions, this skill is **per-repo** in a multi-project
workspace.

---

## Phase: learning

**Trigger:** the user asks to get up to speed, review where things
stand, or set direction — or a batch of findings has landed since the
last learning session and nobody has synthesised them. These sessions
are the project's steering mechanism; run one at a regular cadence
rather than only when lost.

The human's understanding is a first-class artifact of the project —
this phase maintains it the way the notebook maintains the written
record. The protocol:

1. **Assemble the delta.** Find the last learning session (search
   `notebook/log/` for the most recent `## Session — learning` entry;
   if none exists, this is the first — orient from `INDEX.md` alone).
   Collect what changed since: new log entries, notes whose changelog
   moved, new/updated experiments, completed-task debriefs.
2. **Walk it, don't dump it.** Present the delta as a narrative in
   dialogue with the user, most significant findings first, linking
   each claim to its note. Pause for questions; this is a
   conversation, not a report.
3. **Stress the live notes.** For the notes that bear on the next
   decision, explain them back and probe the user's model of them —
   *why* did the result come out that way, what would falsify it,
   which assumption is load-bearing? Where explaining a note exposes
   a gap, ambiguity, or staleness in the note itself, fix the note in
   the session (`notebook:` chores). Explanation failing is the best
   note-quality test there is.
4. **Set direction.** Converge with the user on what's next: the
   question to attack, the experiment to run, or the theory to
   develop — and, briefly, the options *not* taken and why. Record it
   as today's log entry (`## Session — learning`) ending with a
   **Direction** block, and update `INDEX.md`'s open questions if
   they shifted.

Output contract: an updated day log with a Direction block, any note
repairs committed, and a user who can state the project's position in
their own words. If the session surfaces work directly (a correction
task, a missing probe), hand those to the planning phase rather than
filing mid-conversation.

---

## Phase: planning

**Trigger:** a direction exists (usually from a learning session) and
the user wants the work broken down.

Planning here is thin by design — task-cycle already owns filing
mechanics ("Filing a new task"). What this phase adds is the research
framing:

1. **Decompose with the user.** Break the direction into tasks sized
   to task-cycle's context rule (one task ≈ one agent's context
   lifetime). Discuss the breakdown before filing; the decomposition
   *is* the design conversation.
2. **Pre-register experiments.** For each task that is an experiment,
   create the `notebook/experiments/<id>-<slug>.md` stub *at filing
   time* with the Hypothesis and Setup sections drafted and
   `verdict:` unset. Writing the hypothesis before the results exist
   is what makes the eventual verdict honest.
3. **Link theory into briefs.** Each task brief's "Context" section
   links the notebook notes it depends on (and the experiment stub,
   if any) — that's how a cold-starting agent inherits the theory
   without a history replay.
4. **File per task-cycle.** Task files, LOG.jsonl entries, filing
   commit(s). Experiment stubs ride in the filing commit; note the
   dependency ordering in `blocked_by` as usual.

Output contract: filed tasks with notebook-linked briefs, experiment
stubs pre-registered, and the direction's log entry updated with the
task IDs it spawned.

---

## Phase: logging

**Trigger:** an experiment concludes, a finding lands, or a conceptual
development is worth capturing — whether or not it happened inside a
filed task. This phase *is* the research-notebook skill's distill step
(see "Working with task-cycle" there), reached from the workflow side:

1. **Settle the experiment note.** Fill Results and Verdict, set
   `verdict:` in frontmatter, record the commit SHA the numbers came
   from. Inconclusive and refuting outcomes get the same care as
   supporting ones.
2. **Propagate to the theory.** Update or create the `notes/` the
   result bears on; flip statuses (`overturned` / `superseded`) with
   top-of-body callouts where a premise died; append correction
   callouts to old log entries the result invalidates.
3. **Log and re-map.** Append today's log entry; update `INDEX.md`
   (open questions answered, ruled-out list grown, map re-grouped).
4. **Commit** — inside the task's housekeeping commit when a task
   drove the work, else `notebook: <what>`.

The gate from research-notebook applies: chores and plumbing produce
no logging phase at all — their debrief is the whole record.

Output contract: a notebook a cold reader can trust again, which is
precisely what the next learning session's step 1 consumes. That
closure is the point of the cycle.

---

## Cadence and drift

- If a learning session keeps re-explaining the same confusion, the
  note it lives in is bad — rewrite the note, don't re-explain.
- If logging keeps finding the INDEX stale, distills are being
  skipped — tighten the completion habit rather than batch-fixing.
- If planning keeps producing tasks that stall on ambiguity, the
  direction was under-specified — return to learning rather than
  refining briefs in place.

When the user asks "where were we?" mid-cycle, that's a lightweight
learning step 1–2 (assemble and walk the delta), not the full
protocol.
