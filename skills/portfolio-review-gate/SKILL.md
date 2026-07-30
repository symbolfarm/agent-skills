---
name: portfolio-review-gate
description: >-
  Use when a scheduled or interactive checkpoint should inspect a multi-project
  portfolio, proactively propose bounded next-job options, send a short
  approval-oriented digest, and open a discussion about the next portfolio-cycle
  allocation without editing plans, tasks, or strategy. Designed for recurring
  WhatsApp reminders in low-attention mode.
metadata:
  author: symbolfarm
  version: "2"
  authored_by: user
  status: approved
---

# Portfolio review gate

## Overview

Create a concise, read-only checkpoint between unattended portfolio execution
and the next interactive `portfolio-cycle` planning session. The gate answers:

1. Is an approved portfolio batch still running or awaiting reconciliation?
2. Is anything genuinely ready for human review or decision?
3. What useful bounded jobs could advance the active programme next?
4. Which option should the user approve, revise, or reject?

The gate has **proposal autonomy**. When no suitable job is queued, it should
inspect current direction and derive a small set of unfiled candidate jobs rather
than defaulting to inactivity. It recommends one option but cannot approve, file,
schedule, or execute its own proposal. Silence never grants authority.

Use `portfolio-cycle` after the user replies and wants to discuss, shape,
approve, freeze, render, or deploy work.

## When to use

Use this skill for:

- nightly, weekly, or fortnightly portfolio review reminders;
- a short WhatsApp digest before another execution allocation;
- checking whether a portfolio is already running without asking the user to
  replay repository history;
- surfacing a genuine milestone review or consequential decision;
- proactively proposing next-job options when the active queue is empty, blocked,
  stale, or strategically unconvincing;
- recommending a deliberately idle cycle when no responsible option can be
  derived from current evidence.

Do not use it for:

- changing portfolio strategy or project priority;
- filing, splitting, rewriting, or reprioritising project tasks;
- freezing plans, rendering payloads, or creating cron jobs;
- executing project work;
- routine per-commit reporting;
- reviving parked projects merely to fill capacity.

## Authority boundary

A review-gate run is strictly read-only.

It may:

- read portfolio and project evidence;
- inspect Git status and recent history;
- distinguish material milestones from routine activity;
- identify already-filed pending work and approved autonomy envelopes;
- derive one to three **unfiled proposal options** from the active programme's
  documented direction, evidence gaps, milestones, and recently completed work;
- recommend one option and explain why it is the best next bounded job;
- ask one ordinary conversational approval question.

It must not:

- edit or create any file;
- change Git state;
- change task status or create task briefs;
- alter project membership, rank, attention lanes, or automation policy;
- freeze, supersede, or render a portfolio plan;
- create, update, pause, resume, run, or remove cron jobs;
- present an unfiled option as queued, approved, or executable authority;
- treat a recommendation, unanswered question, or user silence as approval;
- infer that available capacity alone is a reason to allocate work.

Proposal autonomy is permission to reason ahead, not permission to mutate state.
If the user approves a proposal, continue interactively under `portfolio-cycle`
and shape the project-local task before any schedule is frozen or deployed.

## Evidence collection

Default portfolio repository: `/workspace/project-portfolio`.

Start with:

1. `PORTFOLIO.md` for current attention lanes and latest stated outcome;
2. `PROJECTS.json` for registry and automation policy;
3. `DECISIONS.md` for unresolved decisions and milestone reviews;
4. `LOW-ATTENTION-MODE.md` when present;
5. the newest dated file in `reviews/`;
6. the newest relevant plan and deployment manifest, when present.

Then inspect the active programme, current incubator, or a project named by an
unresolved review. For those repositories, read their `AGENTS.md`, `TASKS.md`,
`.tasks/LOG.jsonl`, current roadmap/research direction, autonomy envelope when
linked, Git status, and a small recent-commit window as needed.

When no strong queued work exists, inspect enough active-lane evidence to derive
options responsibly. Useful sources include:

- explicit next steps in project documentation and debriefs;
- unresolved research questions or evidence gaps;
- seams exposed by the latest completed milestone;
- missing validation for an already-adopted direction;
- small integrations needed to make completed work usable;
- the next bounded experiment implied by current findings.

Do not tour every parked repository nightly. Parked projects should re-enter the
report only when portfolio evidence explicitly raises them or the user asks about
them. Proposal autonomy does not authorize choosing a new incubator.

Repository state is evidence, not strategy. A clean worktree, passing tests, or
large pending queue does not establish that another batch is valuable.

## Determine the gate state

Classify the checkpoint into exactly one primary state.

### 1. Batch active

Use when the latest approved allocation is still executing or its outcomes are
not yet ready for reconciliation.

Recommendation: let the bounded batch finish. Do not propose dependent follow-up
work before its evidence exists. Mention only a blocking safety or ambiguity
issue if one exists.

### 2. Review required

Use when `DECISIONS.md` or verified project evidence identifies a milestone,
publication, provider, cost, privacy, safety, licensing, or difficult-to-reverse
choice that genuinely needs the user.

Recommendation: review that one item before discussing more execution in its
lane. An unresolved decision parks the affected lane; it does not create a queue
of speculative dependent jobs.

### 3. Queued batch ready

Use when already-filed, pending, unblocked work forms a strategically plausible
next allocation.

Recommend the best allocation at programme or project level. Do not mechanically
select work just because it is pending; explain why it advances current direction.

### 4. Proposal options ready

Use when no sufficiently useful queued batch exists but current active-lane
evidence supports one to three bounded candidate jobs.

Generate the options using the proposal protocol below, recommend one, and ask
whether the user wants it turned into a reviewable task and allocation. The
options remain unfiled and unapproved.

### 5. No responsible proposal

Use only when the active lane is blocked, its direction is too ambiguous, another
batch would exceed an attention or envelope limit, or available evidence cannot
support a useful bounded job.

Explain the stopping reason. Do not manufacture an option. Deliberate inactivity
remains valid, but an empty queue by itself is no longer sufficient reason to
recommend staying parked.

## Proposal autonomy protocol

When the state is `Proposal options ready`, derive one to three options. Prefer
two when there is a real trade-off; use one when the evidence strongly dominates.

Every option must be:

- tied to the current active programme or approved incubator;
- grounded in named repository evidence or recorded portfolio direction;
- bounded enough for one task-cycle job or an explicitly described small batch;
- reversible and locally verifiable;
- free of publication, provider, spending, privacy, safety, licensing, product
  strategy, or difficult-to-reverse architecture decisions;
- clearly labelled **unfiled proposal**.

For each option, communicate four compact elements:

1. **Job:** the concrete outcome, not a vague theme;
2. **Why now:** the evidence or completed milestone that makes it timely;
3. **Produces:** the artifact, test, comparison, review, or decision evidence;
4. **Boundary:** what it will not decide, plus the stopping or escalation point.

Then select one **recommended option** based on strategic fit, information gain,
reversibility, dependency readiness, and expected human-attention cost. Do not
rank by ease alone.

Examples of legitimate proposals:

- a focused source-verification worksheet before an implementation;
- a deterministic comparison experiment after two mechanisms are understood;
- a small integration that exposes an already-completed lab artifact;
- an architecture contract spike that tests one disputed assumption;
- a review of evidence needed to choose between two later approaches.

Examples that are too broad:

- “continue research”;
- “improve the website”;
- “implement the next algorithm” without verified mechanism details;
- “revive a parked project” without an interactive priority decision;
- an open-ended backlog or autonomous multi-step roadmap.

## Nightly report format

Keep the final WhatsApp message short and scannable. Do not use a table.

For active, review, or queued states:

```text
**Portfolio review — <short status>**

- **Since the last cycle:** <one material change, or no material change>
- **Current state:** <batch active / review required / queued batch ready>
- **Recommendation:** <one concrete recommendation>
- **Needs you:** <one review or decision, or “Nothing tonight”>

<One ordinary conversational question.>
```

For proposal autonomy:

```text
**Portfolio review — options for the next batch**

- **Recommended — <job>:** <why now; what it produces; key boundary>
- **Alternative — <job>:** <same compact shape, only when useful>
- **Status:** These are unfiled proposals; nothing has been approved or scheduled.

<Ask whether to turn the recommendation into a reviewable task and allocation.>
```

Formatting rules:

- Aim for 100–220 words; exceed 240 only for a safety-critical explanation.
- Mention at most two attention lanes.
- Present no more than three options and recommend exactly one.
- Include at most one consequential question.
- Do not enumerate routine commits, completed task mechanics, or unchanged parked
  projects.
- Clearly distinguish verified evidence, inferred opportunity, and proposal.
- Never say work is queued, approved, scheduled, or running unless current
  evidence directly establishes it.
- Do not use `[SILENT]` in nightly reminder mode. The reminder itself is desired.
- Invite a free-form reply; do not require an exact phrase or timed selection.

A good proposal closing question is:

> Shall I turn the recommended option into a reviewable task and portfolio
> allocation, or would you like to reshape the options first?

## Continuable WhatsApp jobs

A recurring WhatsApp gate should use:

- `workdir: /workspace/project-portfolio`;
- skills `portfolio-review-gate` and `portfolio-cycle`, in that order;
- delivery to the intended WhatsApp destination;
- `attach_to_session: true` so the user's reply retains the brief;
- read-only toolsets sufficient for files, Git inspection, and skills;
- the configured IANA timezone for the user's wall-clock schedule.

The cron prompt should request `Nightly report mode with proposal autonomy` and
repeat the read-only boundary. Cron jobs run in fresh sessions and cannot rely on
the chat that created them.

A reply starts discussion; it does not itself authorize edits unless the user
explicitly approves filing or scheduling. Once planning begins, follow
`portfolio-cycle`, including its discussion-first and freeze-before-deploy rules.

## Common pitfalls

1. **Turning proposals into task state.** Option text in WhatsApp is not a filed
   task, approved plan, or execution authority.
2. **Being passive when the queue is empty.** Inspect active-lane direction and
   derive bounded options before concluding that nothing is warranted.
3. **Equating pending tasks with strategic priority.** Filed work establishes
   executability, not value. Use current portfolio direction.
4. **Reviewing every parked project nightly.** This creates noise and can revive
   projects accidentally. Inspect only active or explicitly raised lanes.
5. **Manufacturing work.** Proactivity still requires evidence. Use `No responsible
   proposal` when direction is blocked or ambiguous.
6. **Offering a menu without judgment.** Recommend one option and explain the
   trade-off; do not transfer all synthesis work to the user.
7. **Reporting routine commits.** Human review is for milestones and consequential
   decisions, not execution exhaust.
8. **Using fixed UTC for a local-time promise.** Configure an IANA timezone such as
   `Australia/Adelaide` so daylight-saving changes are handled correctly.
9. **Asking several questions.** Choose the one decision that most affects the next
   allocation; park the rest.

## Verification checklist

Before sending the report, verify:

- [ ] No file, task, Git, plan, deployment, or scheduler state was changed.
- [ ] The primary state is one of the five defined gate states.
- [ ] Claims about execution and reviews are backed by current evidence.
- [ ] If useful queued work is absent, active-lane evidence was inspected for
      proposal opportunities.
- [ ] Every derived option is grounded, bounded, reversible, and clearly unfiled.
- [ ] No option silently selects strategy or revives a parked project.
- [ ] Exactly one option is recommended when proposals are presented.
- [ ] The message is concise and contains at most one consequential question.
- [ ] The question invites an ordinary conversational reply.
