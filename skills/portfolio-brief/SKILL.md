---
name: portfolio-brief
description: >-
  Produce the recurring portfolio brief: report goal progress, decisions taken
  under delegated authority, artifacts worth trying, and remaining goal counts;
  propose new goals before the queue runs dry; and surface the small number of
  things that genuinely need the user. Delivers in two forms: a short recurring
  reminder, and the full brief on demand. Use for daily or scheduled chat
  check-ins on the portfolio, whenever the user asks "where is everything up
  to", and whenever they summon the long form from a reminder. Reports and
  proposes; it does not execute, file, or approve.
metadata:
  author: symbolfarm
  version: "14"
  status: draft
  supersedes: portfolio-review-gate
---

# Portfolio brief

## Overview

The brief is the standing report from portfolio execution. It exists so the user can
stay oriented and keep supplying direction without reading repository history.

It answers four questions, in this order:

1. What moved since the last brief, and what can the user *try*?
2. What decisions were taken under delegated authority?
3. How many goals remain, and are any blocked?
4. What, if anything, genuinely needs the user?

The brief is proactive about **direction** and passive about **permission**. Its
default job is asking for goals, not asking for reviews. Running out of goals is
the expected halt condition, not a failure.

## Two forms

The same evidence pass produces two deliveries, and **which one is produced is
set by how the skill was reached**, not by how much happened.

| Form | When | Length |
|---|---|---|
| **Reminder** | the recurring scheduled delivery | 110–180 words or roughly 10–14 short phone-readable lines |
| **Full brief** | summoned from a reminder, invoked directly, or asked for in conversation | 100–260 words, the format below |

The split exists because reading and replying cost differently. A user may read
every recurring delivery and still reply to almost none, and a long report that
is never replied to produces a record of decisions nobody reacted to — which
looks identical to agreement and teaches the calibration ledger nothing. The
reminder is cheap enough to read on a phone and says plainly whether a reply is
even wanted; the full brief is where the reasoning goes, on the occasions the
user asks for it.

**Both forms come from the same evidence pass.** Do the reading described in
**Evidence** either way — including the gap check, which leads the reminder as
well. The reminder is a shorter rendering, never a shallower one; a reminder
assembled without the evidence pass is a guess with a timestamp on it.

**Proposals, scoring, and recommendations belong to the full brief only.** When
the queue is short, the reminder says so after the queue window and summons the
long form; it does not carry the proposal itself.

This skill replaces `portfolio-review-gate`. The old skill was a gate: its
question was whether another batch should be allowed to run. Under the goal-queue
model, work runs continuously until the queue empties or something blocks, so the
useful question became *what should happen next* rather than *may anything happen
at all*.

## Authority

The brief **reports and proposes**. It may:

- read the portfolio repository, project repositories, and Git history;
- write its own dated entry under `log/` in the portfolio repository;
- derive one to three **unfiled goal proposals** when the queue is short;
- recommend one of them and say why;
- ask one ordinary conversational question.

It must **not**:

- edit any project file, or change Git state in a project;
- add, reorder, or complete goals in `GOALS.md`;
- change project state, tier, or `agent_may` in the registry;
- write to the calibration ledger;
- create, change, or remove scheduled jobs;
- present a proposal as queued, approved, or authorised;
- treat a recommendation, an unanswered question, or silence as approval.

Proposing is permission to reason ahead, not permission to mutate state. If the
user approves a proposal, the goal is added under `portfolio-cycle` and executed
under `work-cycle` — never inside the brief itself.

### The one exception: recording observed fact

Recording what is demonstrably true is not a strategy change, and the registry
going stale between reviews is a real cost — it misroutes runs and it wastes
review time re-establishing what happened. So the brief **may** correct registry
fields that are matters of verifiable fact:

- `visibility`, checked against the repository's actual state;
- a `constraints` string whose stated condition is **demonstrably discharged** —
  a hold naming a task that is now complete, a release that has shipped.

Rules for using it: verify against the repository, never against a log entry's
claim; state the correction in the brief in one clause; and if the correction is
anything other than mechanical — if it needs a judgement about what the field
*should* say — leave it and flag it for the review instead.

Everything else in the registry stays `portfolio-cycle`'s: state, tier,
`agent_may`, notes, and adding or removing projects. Those encode intent, and
intent is the user's.

## Evidence

Portfolio repository: the repo holding `GOALS.md`, `PROJECTS.json`,
`CALIBRATION.md` and `log/`. Point the skill at the deployment's configured
`<portfolio-path>`; no particular filesystem location is required.

Read, in this order:

1. `GOALS.md` — the single priority-ordered queue; position is priority;
2. `PROJECTS.json` — registry: paths, state, tier, what agents may do;
3. `CALIBRATION.md` — which decision classes are **auto**, **report**, or **ask**;
4. the most recent entries under `log/`, including the gitignored
   `log/.pusher-*.md` files the host pusher leaves — fold what they record into
   your own committed entry, since the pusher deliberately cannot commit;
5. the derived merged item view, when the portfolio provides one, or otherwise
   the open task records of active repositories — use it to find assignee-marked
   user work and implementation tasks without copying their state;
6. `briefs/` — count of decision briefs awaiting a ruling.

Then inspect the projects that actually moved: Git log since the last brief,
goal-relevant state, and anything a goal's *done-when* refers to. Do not tour
projects that did not move, and do not inspect `parked` or `archived` projects
unless a goal or the user names them.

Repository state is evidence, not strategy. A clean worktree, a passing test
suite, or a long queue does not by itself establish that anything valuable
happened.

### Gap check — lead with silence

**Before anything else, establish when the lane last actually produced
something,** and if that was not since the previous brief, say so in the brief's
first line.

A scheduled lane can stop for reasons no agent inside it can see: the machine was
off, the network was down, the scheduler did not fire, credentials expired. From
inside, every one of these looks identical to a quiet week — and a brief that
reports the queue as though the last run happened normally actively conceals the
outage. The user then discovers it only by asking, which is the one thing the
brief exists to prevent.

So compute the gap from evidence, not from assumption:

- the timestamp of the most recent `log/` entry and the most recent commit in the
  portfolio repository;
- the most recent successful scheduled run of any kind;
- whether the host pusher's latest `log/.pusher-*.md` records a refusal, and for
  how many consecutive runs;
- unmatched claims older than the deployed lane's wind-down interval. Resolve
  `scripts/lifecycle_guard.py` from the installed `work-cycle` skill and run:

  ```bash
  python3 <work-cycle-skill>/scripts/lifecycle_guard.py stale-claims \
    <portfolio>/GOALS.md --older-than-minutes <lane-wind-down-minutes>
  ```

  Use the actual deployed wind-down interval, not a guessed universal default.
  A non-zero result is reportable evidence, not a brief failure: name the stale
  goal and claimant in the gap line. The detector reports only unmatched claims
  still in the executable queue; a matched completion/block and a fresh claim
  are controls, not incidents. **Never auto-release a stale claim.** Rebuilding
  or resuming abandoned work is a judgement for the next operator or the user.

If runs are landing normally, say nothing — this must not become a line of
boilerplate on every healthy day. If there is a gap, open with it:

> *No runs since Sun 9 Mar — three scheduled cycles missed. Cause not visible
> from here; the pusher has refused every run since, which is consistent with an
> outage rather than a code failure.*

State the gap and the best-supported explanation, and **do not diagnose past the
evidence**. "The machine may have been off" is a hypothesis; "the pusher refused
eleven repositories for network or auth reasons" is a fact. Give the user the
fact and let them supply the cause — they usually know it instantly, and it is
almost never something an agent can fix.

### Freshness check

Before writing the brief, reconcile the registry against what the last
`work-cycle` outcome actually did. This is deliberately shallow
— seconds, not a tour — and covers only the projects that moved:

- does recorded `visibility` match the repository?
- does any `constraints` hold name work that has since completed?
- does any project the log says was archived still carry `agent_may`?
- is a goal in `GOALS.md` claimed against a project the registry no longer
  permits?

Correct the two mechanical fields under the exception above; report the rest as
drift for the review to settle. Drift is worth one line in the brief even when
you fixed it, because a field that goes stale repeatedly is evidence about the
process, not about the field.

The deeper reconciliation — whether a project is in the right *state*, whether
`agent_may` still reflects intent, whether the queue's shape still matches where
the work is going — belongs to `portfolio-cycle`, alongside choosing new goals.

## Reporting decisions

Every decision taken under a provisional default is reported according to its
class in `CALIBRATION.md`:

| Class status | In the brief |
|---|---|
| **auto** | Not mentioned. The user has stopped wanting these. |
| **report** | Named in one clause, with the choice made. Grouped, not enumerated. |
| **ask** | Should not have been taken at all — escalate it as a blocker. |

Group `report` decisions into a single line where possible: *"Decisions (3):
serde_json over a custom parser; JSON Lines for export; error copy reworded."*
Detail goes in the `log/` entry, not the message.

Reversibility remains an explicit execution gate: an irreversible decision must
not be taken and appears as a blocker. In the brief, reversibility is implicit
for ordinary `report` decisions under that standing contract. State it only when
it is non-obvious; always state irreversibility when consultation is required.

## Goal count

Report the raw queue state rather than estimating calendar runway: goals in
progress, waiting, and blocked. The count is the anti-stall mechanism—the brief
asks for direction before the queue empties without pretending that scheduled
runs map cleanly to completion days.

- **4 or more unblocked goals:** report the count, ask nothing.
- **2–3 unblocked goals:** mention that goal scoping will soon be useful.
- **0–1 unblocked goals, or all remaining goals blocked:** propose goals using
  the protocol below. Do not simply report that there is nothing to do.

An empty queue is never a reason to conclude that nothing is warranted. It is
the trigger for a proposal.

## Proposing goals

When the goal count is short, derive one to three candidate goals. Prefer two
when there is a real trade-off; one when the evidence clearly dominates.

Ground every proposal in named evidence: an explicit next step in project
documentation, an unresolved question, a seam exposed by finished work, missing
validation for an adopted direction, or a small integration that would make
completed work usable.

Each proposal must be:

- tied to an `active` project in the registry;
- bounded enough for one `work-cycle` run;
- expressed with a concrete **done-when** that someone else could check;
- free of decisions in an **ask** class;
- clearly labelled an **unfiled proposal**.

Score each on both axes, and say so:

- **Produces something usable** — does it yield a working artifact?
- **Teaches us about working with agents** — does it inform how we build with,
  coordinate, or supervise agents?

Aim for goals scoring high on both. A goal scoring low on both is the clearest
possible drop. High on only one is legitimate, but say which one.

Then recommend exactly one, on strategic fit, information gain, reversibility,
and dependency readiness. Do not rank by ease. Do not hand the user a menu with
no judgment attached — that transfers the synthesis work back to them, which is
the cost the whole system exists to avoid.

Do not propose reviving a `parked` project. That is a priority decision, and it
belongs in an interactive `portfolio-cycle` session.

## Pointing at artifacts

Where a goal produced something the user could experience, **give them the way
in, not a description of it**: a command to run, a path to open, a published
artifact link, a branch to check out.

This is the highest-leverage review instrument available, so it is worth a line
in the brief every time it applies. It is always **suggested, never required** —
the user ignores it freely and that is a valid outcome.

For work that is understood rather than run — a design, an experiment, a
mechanism — prefer a pinned visual: a mermaid diagram or self-contained HTML
page, published as an artifact so it is readable on a phone.

## Adversarial self-report

When a goal completes, name in one clause the part the author would attack if
reviewing it — the weakest assumption, the least-tested path, the thing most
likely wrong. Omit it only when there is genuinely nothing; do not manufacture
false modesty, and do not let it become boilerplate.

This is cheap to produce and falsifiable: confidence that later proves misplaced
is calibration evidence.

## Decision briefs

Research decision briefs are read in a working session, not on a phone. Report
only the count and the oldest:

> *Decision briefs: 3 waiting, oldest 4 days (retrieval keying strategy).*

Do not summarise their content, and do not apply a cap to how many may
accumulate — they are read in a block, and throttling them would throttle the
one channel where the user wants throughput.

## Ending: state the next goal, do not ask for it

The brief **closes by saying what happens next**, as a statement:

> *Next: G-002, the puzzle-site closeout, starting on the next run.*

An identifier alone is not orientation. Always include a short plain-language
gist after the ID — normally three to eight words from the goal title, enough
to understand the intended outcome without opening `GOALS.md`. `Next: G-027`
is invalid; `Next: G-027 — compare frozen-base parameter additions` is useful.

The named goal must be the goal the deployed executor would actually select,
not merely the first agent-assigned row in the raw queue. Apply its explicit
lane allocation, capabilities, gates, assignees, claims, and repository
availability, preserving queue order within each eligible set. Lane allocation
is routing, not a second strategic priority. If selection differs from the first
raw queue entry, name the decisive reason rather than concealing the mismatch.

Not *"shall I take G-002?"*. The execution model already proceeds on reversible
work without waiting for permission; a brief that asks permission to continue
contradicts it, and it puts the user back in the loop the system exists to keep
them out of. Silence means proceed.

Ask a question **only** when something genuinely blocks — a decision in an `ask`
class, an irreversible action, an empty queue, or a contradiction between the
queue and the registry — or when routing the highest-ranked user-assigned item
that does not require a computer. A blocker question replaces the next-goal line.
A user-item question may appear alongside the next-goal statement because the
user and agent queues advance independently. In either case ask exactly one
ordinary conversational question; never turn the brief into a menu.

Mark the end of the brief plainly, so it is obvious where the report stops and
any surrounding conversation starts.

## User-assigned items

Filter the merged item view for `assignee: <user>`. Report the count, anything
blocking, and the age of the oldest item. Put the top item forward in the full
brief. In the recurring reminder, show up to two top-ranked user items that are
not already visible in its queue window. Do not maintain a second checklist in
prose.

> *Yours: 4 open, 1 blocking. Oldest 12 days.*
> *Today's one: the pusher is still off, which blocks G-002. The remaining step
> is enabling the systemd unit on the host — about two minutes. Want it back on?*

A count alone does not move this queue. It reports a number the user already
feels bad about and asks nothing, so nothing happens. The full brief still asks
for at most one decision; the reminder's optional second row supplies context,
not a second question.

The rules that keep this a prod rather than a guilt-list:

- **One actionable ask; at most two reminder rows.** The full brief puts one item
  forward. The reminder may show a second top-ranked item when it is outside the
  queue window, but asks at most one question. Never expand this into a backlog.
- **A gated item is not eligible — filter before ranking.** The merged view
  marks an item whose gate is still open as `gated by <id> (open)`, derived from
  the `Blocks:` list of an item that has not landed. Never put such an item
  forward: the user provably cannot start it, and one unstartable ask costs the
  line the credibility that is its entire value. Report it in the count and in
  the blocking summary; put the *gate* forward instead when the gate is itself
  the user's, and otherwise take the next eligible item. If every user item is
  gated, report that fact without pretending one is actionable.
- **Rank, do not rotate.** Choose in this order: anything blocking a goal, then
  anything **decaying** — where waiting makes the item worse or the opportunity
  smaller — then the cheapest to close. Prefer one that can be answered in a
  single reply. An item that `Blocks:` other work outranks one that gates
  nothing, because closing it unblocks the queue behind it.
- **The same item may be surfaced on consecutive briefs, and should be if it is
  still the top-ranked one.** This rule previously said to rotate, on the theory
  that repetition becomes noise. Rotation is a fairness heuristic, and fairness
  is not what the user needs from this queue: it will cheerfully show a stale
  item while a decaying one gets quietly worse. Corrected at a user's explicit
  direction — *some things are more urgent, and should be brought up on repeat
  until they happen.*
- **State the smallest next action and the honest size**, not the item's title.
  "Enable the systemd unit, about two minutes" is actionable; "the pusher
  rollout" is a project.
- **Do not diagnose an item that keeps not moving.** Report that it has been
  put forward *n* times and let the user say why. This rule previously said to
  stop asking after three strikes and propose a reshape or a drop instead —
  which is an inference the user previously corrected. The ordinary cause is
  that the user is short of time
  and energy, not that the item is mis-shaped, and an agent that reshapes a
  neglected item is sounding thoughtful while letting the backlog rot.
  Only the user drops or reshapes their own items.

The brief does not add, complete, or reshape items; its authority remains
report-only. If evidence shows an item is already done, report the discrepancy
for the next `portfolio-cycle` session rather than silently mutating the queue.
Report age as a fact and let the user say whether it reflects neglect, shape, or
changed priority.

## The reminder

The recurring form is a compact **queue window**, not merely a conclusion. It
shows enough raw order and routing state for the user to see why the selected
goal is next. Prefer 110–180 words or roughly 10–14 short phone-readable lines;
structure and scanability matter more than a rigid word count.

```text
**Portfolio — Tue 5 Mar** · 1 done, 8 queued

Done: G-012 — stable manifest identity

Queue:
1. G-014 — finish export path · agent · ready
2. G-002 — puzzle-site closeout · agent · blocked: pusher off
3. G-018 — enable host pusher · owner · requires computer; gates G-002
4. G-021 — compare import formats · agent · gated by G-014
5. G-024 — visual review · agent · skipped: needs Chrome

Anomalies: 1 — tree-editor dirty since Mon; untracked scratch file
Selected next: G-014 — finish the export path · agent · ready
Yours: G-026 — approve release wording · phone-ready, ~2 min

Reply freely, or ask for the full brief or review.
— end —
```

Rules:

- **Lead with the gap** when the lane has been silent since the last delivery,
  exactly as the full brief does. A reminder that reports a queue during an
  outage conceals the outage more cheaply, not less.
- Show the first five open goals in actual `GOALS.md` order. Continue through
  position six or seven only when doing so reaches the selected goal; otherwise
  stop at five and show the selection separately.
- Format every queue row as `<position>. <ID> — <plain-language gist> ·
  <owner> · <state/reason>`. Use the configured owner's display name rather
  than generic `human`.
- Use a compact state vocabulary: `ready`, `claimed`, `<owner> · requires
  computer`, `skipped: needs <capability>`, `gated by <ID>`, and `blocked:
  <reason>`. Do not invent a status when the evidence does not establish one.
- Completed work stays in `Done`, not in `Queue`. The queue means executable or
  waiting open work; mixing completed items into it destroys that meaning.
- Omit any section with nothing in it. Do not print empty lines merely to keep a
  visual skeleton.
- **Never carry a proposal, a recommendation, or a scored option.** If the queue
  is short, say so after the queue window and point at the full brief.
- Close with the actual executor-selected next goal, its short plain-language
  gist, owner, state/reason, and how to summon both longer forms. If the selected
  goal is outside the queue window, say briefly why: capability skip, gate, user
  assignment, existing claim, repository unavailable, or explicit lane
  allocation. The user must never have to remember an exact phrase — accept any
  plain request.

### Yours rows

After the selected-next line, show up to two highest-ranked user items that did
not already appear in the queue window. Suppress duplicates; if a top user item
is already visible, the queue row has done the job.

- Rank as **User-assigned items** specifies: filter gated items first, then
  blocking, decaying, and cheapest. An item that gates more work outranks one
  that gates less.
- Include `Requires: computer` honestly. The reminder is an orientation surface,
  not only a phone-action surface; an item can be worth seeing while currently
  impossible to perform.
- Give the short outcome gist and smallest next action. Include an honest size
  only when evidence supports one.
- Ask at most one question across the entire reminder. A second Yours row is
  context, never a second demand.
- If no actionable user item exists outside the queue window, omit `Yours`
  rather than padding the reminder with `nothing`.

## Anomaly items

An anomaly item is a queue entry a `work-cycle` run filed to record an
obstruction it refused to clear — normally a repository it could not work
because the worktree was dirty or another agent held its lock. `work-cycle`
marks it with an `*Anomaly:*` line naming the repository and what was found.

**Report anomalies on their own line, never inside the goal count.** An anomaly
is not work someone chose; it is the lane reporting that it routed around
something. Counting it as a goal makes an obstruction look like planned work,
and — worse — makes a lane that is silently skipping items look like a lane with
a healthy backlog.

- Give the count, the repository, and how long it has stood.
- **An anomaly standing for more than one run is the story, not the backlog.**
  Repetition here means the lane is losing the same items every run.
- If the residue is the user's to rule on, it is a candidate for the first
  `Yours` row and usually outranks anything else, because it is blocking by
  construction.
- The brief does not clear it, and does not guess what an untracked file was
  for. Report the fact; the user supplies the cause.

## Format — the full brief

Short and scannable. No tables. Aim for 100–220 words; exceed 260 only for a
safety issue.

```text
**Portfolio — Tue 5 Mar**

Goals: 1 done, 2 advanced, 4 remaining; none blocked

- **G-012 done** — manifest identity in the tree editor.
  Try it: `cd tree-editor && npm run demo` — export twice, diff the manifests.
  Weakest point: only tested on trees under 100 nodes.
- **G-014** in progress, no blockers.

Decisions (3): serde_json over a custom parser; JSON Lines for
export; error copy reworded. Details in log/2026-03-05.md.

Decision briefs: 3 waiting, oldest 4 days.
Yours: 2 open, none blocking. Oldest 5 days.
Today's one: the SpecSoloist roadmap session — 30 minutes to decide what the
project is for, which unblocks the deferred floor raise. Worth booking?

Next: G-014, finishing the export path. Then G-015.
— end of brief —
```

Rules:

- Open with the gap when the lane has been silent since the last brief; say
  nothing about it when runs are landing normally.
- Mention at most three goals; group the rest into counts.
- Close with the next goal. Ask nothing unless something genuinely blocks.
- At most one question, only for a genuine blocker or the one phone-routable
  user-assigned item selected by the brief. Park the others.
- Never enumerate routine commits or task mechanics.
- Distinguish clearly between verified fact, inference, and proposal.
- Never say a goal is done, queued, or approved unless evidence establishes it.
- Invite a free-form reply. Never require an exact phrase or a timed response.
- The brief is wanted — do not suppress it because nothing dramatic happened.

## Pitfalls

1. **Reporting activity instead of progress.** Commits are exhaust. Report goals
   moved and artifacts produced.
2. **Going quiet when the queue empties.** An empty queue is the moment to
   propose, not to report inactivity.
3. **Describing an artifact instead of handing it over.** A summary is the most
   expensive and least accurate way for the user to judge the work.
4. **Reporting `auto` decisions.** The ledger exists so the brief gets shorter
   over time. Honour it.
5. **Treating a proposal as filed.** Text in a message is not a queued goal.
6. **Offering options without a recommendation.** Choose one and justify it.
7. **Touring parked projects.** Noise, and it risks reviving them by accident.
8. **Asking permission to continue.** The brief states the next goal. Asking
   puts the user back in the loop the system exists to keep them out of.
9. **Fixed UTC for a local-time promise.** Use the configured IANA timezone so
   daylight saving is handled.
10. **Showing a queue without reasons.** IDs and titles alone still conceal why
    work is skipped, gated, or selected out of raw order.
11. **Sending a long report on the recurring schedule.** The reminder is the
    recurring form. The full brief is summoned.
12. **Counting an anomaly item as a goal.** It makes a lane that is skipping
    items look like a lane with work queued.
13. **Putting a gated item forward.** An item the merged view marks `gated by
    <id> (open)` cannot be started, so offering it as a `Yours` action is the
    fastest way to make the reminder unbelievable.

## Before sending

- [ ] The form matches how the skill was reached: reminder when recurring, full
      brief when summoned or asked for.
- [ ] The reminder contains the first five open queue rows, or continues only to
      a nearby selected goal at position six or seven.
- [ ] Every queue row has position, ID, gist, owner, and evidence-backed
      state/reason.
- [ ] Completed goals are outside the queue window.
- [ ] Up to two non-duplicated `Yours` rows appear only when their items are not
      already visible; at most one question is asked.
- [ ] The item put forward is not marked `gated by <id> (open)` in the merged
      view.
- [ ] Anomaly items are reported on their own line and excluded from the goal
      count.
- [ ] The gap since the last successful run was checked, and led the brief if
      there was one; the stale-claim detector was run with the deployed lane's
      wind-down interval.
- [ ] Nothing was edited outside the portfolio `log/` entry.
- [ ] Every completion claim is backed by checked evidence.
- [ ] Decisions are reported at the level `CALIBRATION.md` specifies.
- [ ] No decision in an **ask** class was taken silently.
- [ ] Goal counts are stated, and a short queue triggered scoping or proposals.
- [ ] Any proposal is grounded, bounded, scored on both axes, and marked unfiled.
- [ ] Exactly one option is recommended when proposals are present.
- [ ] Completed work names its weakest point.
- [ ] Where something is runnable or readable, the way in is included.
- [ ] The brief closes by stating the next goal, not by asking for one.
- [ ] The next-goal line includes a plain-language gist and matches the deployed
      executor's explicit lane allocation and capability policy.
- [ ] A question appears only for a genuine blocker or the one routed
      user-assigned item.
- [ ] The end of the brief is plainly marked.
