---
name: portfolio-review-gate
description: >-
  Use when a scheduled or interactive checkpoint should inspect a multi-project
  portfolio, send a short approval-oriented digest, and open a discussion about
  the next bounded portfolio-cycle allocation without editing plans, tasks, or
  strategy. Designed for recurring WhatsApp reminders in low-attention mode.
metadata:
  author: symbolfarm
  version: "1"
  authored_by: user
  status: approved
---

# Portfolio review gate

## Overview

Create a concise, read-only checkpoint between unattended portfolio execution
and the next interactive `portfolio-cycle` planning session. The gate answers:

1. Is an approved portfolio batch still running or awaiting reconciliation?
2. Is anything genuinely ready for human review or decision?
3. Is there enough authorized, useful work to justify discussing another batch?
4. What is the single best next conversation for the user to have?

The gate is a reminder and conversation opener, not a planner or dispatcher. It
may inspect evidence and recommend discussion. It cannot approve its own
recommendation or turn silence into consent.

Use `portfolio-cycle` after the user replies and wants to discuss, shape,
approve, freeze, render, or deploy work.

## When to use

Use this skill for:

- nightly, weekly, or fortnightly portfolio review reminders;
- a short WhatsApp digest before another execution allocation;
- checking whether a portfolio is already running without asking the user to
  replay repository history;
- surfacing a genuine milestone review or consequential decision;
- recommending that no new batch be scheduled when useful work is not ready.

Do not use it for:

- changing portfolio strategy or project priority;
- filing, splitting, rewriting, or reprioritising project tasks;
- freezing plans, rendering payloads, or creating cron jobs;
- executing project work;
- routine per-commit reporting;
- manufacturing work merely because the reminder fired.

## Authority boundary

A review-gate run is strictly read-only.

It may:

- read portfolio and project evidence;
- inspect Git status and recent history;
- distinguish material milestones from routine activity;
- identify already-filed pending work and approved autonomy envelopes;
- recommend `proceed to discussion`, `review first`, `wait`, or `stay parked`;
- ask one ordinary conversational question.

It must not:

- edit or create any file;
- change Git state;
- change task status or create task briefs;
- alter project membership, rank, attention lanes, or automation policy;
- freeze, supersede, or render a portfolio plan;
- create, update, pause, resume, run, or remove cron jobs;
- treat a recommendation, unanswered question, or user silence as approval;
- infer that available capacity is a reason to allocate work.

If the evidence is ambiguous, report the ambiguity and recommend waiting. Do
not repair it during the gate run.

## Evidence collection

Default portfolio repository: `/workspace/project-portfolio`.

Start with the smallest useful evidence set:

1. `PORTFOLIO.md` for current attention lanes and latest stated outcome;
2. `PROJECTS.json` for registry and automation policy;
3. `DECISIONS.md` for unresolved decisions and milestone reviews;
4. `LOW-ATTENTION-MODE.md` when present;
5. the newest dated file in `reviews/`;
6. the newest relevant plan and deployment manifest, when present.

Then inspect only the active programme, current incubator, or a project named by
an unresolved review. For those repositories, read their `AGENTS.md`,
`TASKS.md`, `.tasks/LOG.jsonl`, autonomy envelope when linked, Git status, and a
small recent-commit window as needed.

Do not tour every parked repository every night. Parked projects should re-enter
the report only when portfolio evidence explicitly raises them or the user asks
about them.

Repository state is evidence, not strategy. A clean worktree, passing tests, or
large pending queue does not establish that another batch is valuable.

## Determine the gate state

Classify the checkpoint into exactly one primary state:

### 1. Batch active

Use when the latest approved allocation is still executing or its outcomes are
not yet ready for reconciliation.

Recommendation: wait for the bounded batch to finish. Mention only a blocking
safety or ambiguity issue if one exists.

### 2. Review required

Use when `DECISIONS.md` or verified project evidence identifies a milestone,
publication, provider, cost, privacy, safety, licensing, or difficult-to-reverse
choice that genuinely needs the user.

Recommendation: review that one item before discussing more execution in its
lane. An unresolved decision parks the affected lane; it does not create a
queue of follow-up questions.

### 3. Ready to discuss a batch

Use only when there is a plausible next allocation backed by at least one of:

- already-filed pending and unblocked project work;
- an approved project-local autonomy envelope with remaining iteration budget;
- an explicitly recorded portfolio recommendation awaiting discussion.

Describe the proposal at programme or project-allocation level. Do not invent
exact task briefs. State why this batch appears more valuable than leaving the
capacity unused.

### 4. No warranted batch

Use when there is no meaningful review and no sufficiently authorized,
strategically justified next allocation.

Recommendation: keep the portfolio idle or parked. This is a successful gate
outcome, not a failure to find work.

## Nightly report format

Keep the final WhatsApp message short and scannable. Do not use a table.

```text
**Portfolio review — <short status>**

- **Since the last cycle:** <one material change, or no material change>
- **Current state:** <batch active / review required / ready to discuss / no warranted batch>
- **Recommendation:** <one concrete recommendation>
- **Needs you:** <one review or decision, or “Nothing tonight”>

<Question inviting an ordinary conversational reply.>
```

Formatting rules:

- Aim for 80–160 words; exceed 200 only for a safety-critical explanation.
- Mention at most two attention lanes.
- Include at most one consequential question.
- Do not enumerate routine commits, completed task mechanics, or unchanged
  parked projects.
- Clearly distinguish verified evidence from a recommendation.
- Never say work is “approved”, “scheduled”, or “running” unless the evidence
  directly establishes it.
- Do not use `[SILENT]` in nightly reminder mode. The reminder itself is desired.
- Invite a free-form reply; do not require an exact phrase or timed option
  selection.

When no action is warranted, a good closing question is:

> Shall we leave the portfolio parked tonight, or is there a priority you want
> to discuss for the next cycle?

## Continuable WhatsApp jobs

A recurring WhatsApp gate should use:

- `workdir: /workspace/project-portfolio`;
- skills `portfolio-review-gate` and `portfolio-cycle`, in that order;
- delivery to the intended WhatsApp destination;
- `attach_to_session: true` so the user's reply retains the brief;
- read-only toolsets sufficient for files, Git inspection, and skills;
- the configured IANA timezone for the user's wall-clock schedule.

The cron prompt should request `Nightly report mode` and repeat the strict
read-only boundary. Cron jobs run in fresh sessions and cannot rely on the chat
that created them.

A reply starts discussion; it does not itself authorize edits unless the user
explicitly requests or approves them. Once planning begins, follow
`portfolio-cycle`, including its discussion-first and freeze-before-deploy
rules.

## Common pitfalls

1. **Turning the digest into a full portfolio cycle.** Stop after the compact
   evidence summary, recommendation, and one question.
2. **Equating pending tasks with strategic priority.** Filed work establishes
   executability, not value. Use current portfolio direction.
3. **Reviewing every parked project nightly.** This creates noise and can revive
   projects accidentally. Inspect only active or explicitly raised lanes.
4. **Inventing a batch to make the cron useful.** “No warranted batch” is often
   the most useful result.
5. **Reporting routine commits.** Human review is for milestones and
   consequential decisions, not execution exhaust.
6. **Allowing the reminder to mutate state.** A gate that edits plans or tasks is
   no longer a gate.
7. **Using fixed UTC for a local-time promise.** Configure an IANA timezone such
   as `Australia/Adelaide` so daylight-saving changes are handled correctly.
8. **Asking several questions.** Choose the one decision that most affects the
   next allocation; park the rest.

## Verification checklist

Before sending the report, verify:

- [ ] No file, task, Git, plan, deployment, or scheduler state was changed.
- [ ] The primary state is one of the four defined gate states.
- [ ] Claims about execution and reviews are backed by current evidence.
- [ ] Any proposed batch uses already-filed work or an approved autonomy envelope.
- [ ] The recommendation allows “do nothing” when that is strategically sound.
- [ ] The message is concise and contains at most one consequential question.
- [ ] The question invites an ordinary conversational reply.
