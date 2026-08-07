---
name: portfolio-brief
description: >-
  Produce the recurring portfolio brief: report goal progress, decisions taken
  under delegated authority, artifacts worth trying, and remaining goal runway;
  propose new goals before the queue runs dry; and surface the small number of
  things that genuinely need the user. Use for daily or scheduled WhatsApp
  check-ins on the build lane, and whenever the user asks "where is everything
  up to". Reports and proposes; it does not execute, file, or approve.
metadata:
  author: symbolfarm
  version: "3"
  status: draft
  supersedes: portfolio-review-gate
---

# Portfolio brief

## Overview

The brief is the standing report from the build lane. It exists so the user can
stay oriented and keep supplying direction without reading repository history.

It answers four questions, in this order:

1. What moved since the last brief, and what can the user *try*?
2. What decisions were taken under delegated authority?
3. How much goal runway is left?
4. What, if anything, genuinely needs the user?

The brief is proactive about **direction** and passive about **permission**. Its
default job is asking for goals, not asking for reviews. Running out of goals is
the expected halt condition, not a failure.

This skill replaces `portfolio-review-gate`. The old skill was a gate: its
question was whether another batch should be allowed to run. Under the goal-queue
model, work runs continuously until the queue empties or something blocks, so the
useful question became *what should happen next* rather than *may anything happen
at all*.

## Authority

The brief **reports and proposes**. It may:

- read the portfolio repository, project repositories, and Git history;
- write its own dated entry under `log/` in the portfolio repository;
- derive one to three **unfiled goal proposals** when runway is short;
- recommend one of them and say why;
- ask one ordinary conversational question.

It must **not**:

- edit any project file, or change Git state in a project;
- add, reorder, or complete goals in `GOALS.md`;
- change project state, tier, or constraints in the registry;
- write to the calibration ledger;
- create, change, or remove scheduled jobs;
- present a proposal as queued, approved, or authorised;
- treat a recommendation, an unanswered question, or silence as approval.

Proposing is permission to reason ahead, not permission to mutate state. If the
user approves a proposal, the goal is added under `portfolio-cycle` and executed
under `goal-cycle` — never inside the brief itself.

## Evidence

Portfolio repository: `/workspace/portfolio`.

Read, in this order:

1. `GOALS.md` — the single priority-ordered queue; position is priority;
2. `PROJECTS.json` — registry: paths, state, tier, what agents may do;
3. `CALIBRATION.md` — which decision classes are **auto**, **report**, or **ask**;
4. the most recent entries under `log/`, including the gitignored
   `log/.pusher-*.md` files the host pusher leaves — fold what they record into
   your own committed entry, since the pusher deliberately cannot commit;
5. `briefs/` — count of Lane B decision briefs awaiting a ruling;
6. `TOBY.md` — the human queue: what only the user can do, and what is blocking.

Then inspect the projects that actually moved: Git log since the last brief,
goal-relevant state, and anything a goal's *done-when* refers to. Do not tour
projects that did not move, and do not inspect `parked` or `archived` projects
unless a goal or the user names them.

Repository state is evidence, not strategy. A clean worktree, a passing test
suite, or a long queue does not by itself establish that anything valuable
happened.

## Reporting decisions

Every decision taken under a provisional default is reported according to its
class in `CALIBRATION.md`:

| Class status | In the brief |
|---|---|
| **auto** | Not mentioned. The user has stopped wanting these. |
| **report** | Named in one clause, with the choice made. Grouped, not enumerated. |
| **ask** | Should not have been taken at all — escalate it as a blocker. |

Group `report` decisions into a single line where possible: *"Decisions (3, all
reversible): serde_json over a custom parser; JSON Lines for export; error copy
reworded."* Detail goes in the `log/` entry, not the message.

Never report a decision without stating that it is reversible — or, if it is
not, escalating it instead.

## Goal runway

**Runway is the count of remaining unblocked goals, expressed in days at the
current completion rate.** It is the anti-stall mechanism: the brief asks for
direction *before* the queue empties, so the lane never idles waiting to be
noticed.

Calculate completion rate from recent **observed goal outcomes**, not from the
maximum schedule frequency. A daily executor provides at most one opportunity
per day; a partial or blocked run does not become a completed goal merely
because another tick is scheduled tomorrow. Prefer the last three to seven real
runs. With fewer than three runs, report a low-confidence range rather than
false precision—for example, `7 goals (~7–14 days at the early observed rate)`.
Always state the raw remaining-goal count even when the day estimate is uncertain.

- **Runway ≥ 4 days:** report it, ask nothing.
- **Runway 1–3 days:** ask for goals, and offer to propose some.
- **Runway 0, or all remaining goals blocked:** propose goals using the protocol
  below. Do not simply report that there is nothing to do.

An empty queue is never a reason to conclude that nothing is warranted. It is
the trigger for a proposal.

## Proposing goals

When runway is short, derive one to three candidate goals. Prefer two when there
is a real trade-off; one when the evidence clearly dominates.

Ground every proposal in named evidence: an explicit next step in project
documentation, an unresolved question, a seam exposed by finished work, missing
validation for an adopted direction, or a small integration that would make
completed work usable.

Each proposal must be:

- tied to an `active` project in the registry;
- bounded enough for one `goal-cycle` run;
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

## Lane B

The brief covers the build lane. Research decision briefs are read in a working
session, not on a phone. Report only the count and the oldest:

> *Lane B: 3 briefs waiting, oldest 4 days (retention-bench keying strategy).*

Do not summarise their content, and do not apply a cap to how many may
accumulate — they are read in a block, and throttling them would throttle the
one channel where the user wants throughput.

## Ending: state the next goal, do not ask for it

The brief **closes by saying what happens next**, as a statement:

> *Next: G-002, the garden-03 closeout, starting on the next run.*

Not *"shall I take G-002?"*. The execution model already proceeds on reversible
work without waiting for permission; a brief that asks permission to continue
contradicts it, and it puts the user back in the loop the system exists to keep
them out of. Silence means proceed.

Ask a question **only** when something genuinely blocks — a decision in an `ask`
class, an irreversible action, an empty queue, or a contradiction between the
queue and the registry. Then ask exactly one, and it replaces the next-goal line
rather than joining it.

Mark the end of the brief plainly, so it is obvious where the report stops and
any surrounding conversation starts.

## The human queue

`TOBY.md` holds what only the user can do. Report it as a count, plus anything
blocking, plus the age of the oldest item:

> *Yours: 4 open, 1 blocking (enable the pusher — blocks G-002). Oldest 12 days.*

The brief **may add** items that are genuinely blocked on the user, and **may
tick off** items evidence shows are done. It may not invent speculative ones —
see the rules in `TOBY.md` itself. A list anyone can add to becomes a guilt-list
nobody reads, and the blocking items get lost in it.

Report age because a long-sitting item is usually **mis-shaped** rather than
neglected: too big, secretly blocked, or not actually important. Naming the age
prompts reshaping it, which is more useful than another reminder.

## Format

Short and scannable. No tables. Aim for 100–200 words; exceed 240 only for a
safety issue.

```text
**Portfolio — Tue 5 Aug**

Goals: 1 done, 2 advanced, 4 remaining (~3 days runway)

- **G-012 done** — Definitree manifest identity.
  Try it: `cd web-define-tree && npm run demo` — export twice, diff the manifests.
  Weakest point: only tested on trees under 100 nodes.
- **G-014** in progress, no blockers.

Decisions (3, all reversible): serde_json over a custom parser; JSON Lines for
export; error copy reworded. Details in log/2026-08-05.md.

Lane B: 3 briefs waiting, oldest 4 days.
Yours: 2 open, none blocking. See TOBY.md.

Next: G-014, finishing the export path. Then G-015.
— end of brief —
```

Rules:

- Mention at most three goals; group the rest into counts.
- Close with the next goal. Ask nothing unless something genuinely blocks.
- At most one question, and only when blocked. Park the others.
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

## Before sending

- [ ] Nothing was edited outside the portfolio `log/` entry.
- [ ] Every completion claim is backed by checked evidence.
- [ ] Decisions are reported at the level `CALIBRATION.md` specifies.
- [ ] No decision in an **ask** class was taken silently.
- [ ] Runway is stated, and short runway triggered a proposal.
- [ ] Any proposal is grounded, bounded, scored on both axes, and marked unfiled.
- [ ] Exactly one option is recommended when proposals are present.
- [ ] Completed work names its weakest point.
- [ ] Where something is runnable or readable, the way in is included.
- [ ] The brief closes by stating the next goal, not by asking for one.
- [ ] A question appears only if something genuinely blocks.
- [ ] The end of the brief is plainly marked.
