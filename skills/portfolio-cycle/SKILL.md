---
name: portfolio-cycle
description: >-
  Run the interactive portfolio session: a twice-weekly review of what got done,
  what is in flight, and what comes next; re-order the single goal queue; update
  project states and the calibration ledger; and turn agreed direction into
  filed goals. Use when the user asks for a review, wants to set or re-order
  goals, asks where things are up to across projects, or wants to change a
  project's state or trust level. Repository state is evidence; the conversation
  is the source of strategy.
license: MIT
metadata:
  author: Symbol Farm
  version: "6"
  category: productivity
  tags: portfolio, review, goals, planning, multi-project
---

# Portfolio cycle

The interactive session where direction is set. Runs against
`/workspace/portfolio`, works with no scheduler present, and needs nothing from
any particular agent runtime.

`portfolio-brief` reports between sessions. `goal-cycle` executes. This skill is
where the user and the agent decide what should happen.

## The three structures

Keep these strictly apart. Conflating them is what produced the previous
design's overlapping vocabularies.

| File | Answers | Changes |
|---|---|---|
| `PROJECTS.json` | What exists, where, in what state, what agents may do there | Rarely |
| `GOALS.md` | What to do next, in order | Constantly |
| `CALIBRATION.md` | Which decision classes are delegated | Slowly, on evidence |

**Priority is not a property of a project.** It is position in `GOALS.md`. There
is no project rank and no attention level.

## Boundaries

- Discussion is the source of strategy. Repository state is evidence.
- Never file a goal the user has not agreed to.
- Never move a calibration level on a single instance. Patterns only.
- Never revive a `parked` project to fill capacity. Reviving is a priority
  decision, made explicitly.
- Goals belong only to `active` projects with a non-empty `agent_may`.
- Keep task-level detail in the project. A goal names an outcome; `task-cycle`
  and `goal-cycle` decide how.
- One queue. Never a per-project queue.

---

## Session A: the review

**Cadence: once or twice a week.** This is the user's standing reflective
practice — what I have done, what I am doing, what is next — carried over from
research and day-job habit. It works because it is regular, short, and always
the same shape.

The division of labour is the point: **the agent assembles "done" from evidence;
the user supplies "next".** Retrieval and compression are cheap for an agent and
expensive for a person. Direction is the reverse.

### A1. Assemble, before the user arrives if possible

From `log/` entries, `GOALS.md`, project Git history, and `briefs/` since the
last review:

- goals completed, with the artifact each produced;
- goals in flight, and whether any have stalled;
- decisions taken, grouped by calibration class;
- decision briefs ruled on, and any still waiting;
- notebook findings ratified or still provisional;
- anything that turned out differently from what was expected.

Compress hard. The user should not have to reconstruct context. Name artifacts
they can open, not commits they would have to read.

### A2. Present

Three headings, in this order, and nothing else:

**Done** — what actually landed, with what to try. Two or three items, grouped.
**Doing** — what is in flight, and anything stalled with the reason.
**Next** — the current top of the queue, as a proposal to react to.

Say plainly what did not go well. A review that only reports progress stops
being useful within a month.

### A3. Discuss

The user's part. Useful prompts, not a checklist to march through:

- Has anything changed what matters most?
- Is anything in the queue no longer worth doing?
- Did anything take much longer, or turn out much easier, than expected?
- Is anything blocked on them that they want to unblock, drop, or defer?
- Is any project in the wrong state?

### A4. Act on what was agreed

- Re-order `GOALS.md`. Remove goals that no longer earn their place; say so.
- File new goals (§Filing goals below).
- Update project states, tiers, or `agent_may`.
- Update `CALIBRATION.md` counts, and move a level only on a pattern.
- Write the review to `log/YYYY-MM-DD-review.md`.
- Commit. Portfolio changes commit separately from any project work.

### A5. The one question worth asking every time

**Which class of decision cost the user the most attention this week, and can it
move?**

That is what makes the system cheaper over time. Skipping it means the ledger
never moves and every week costs what the last one did.

---

## Session B: scoping

Use when something arrives that is too unsettled to become goals — a new
direction, a possible restructure, a project whose shape is in question.

Do not file goals against an unsettled design. Work has to be discarded for the
wrong reason, and it is the most demoralising kind of waste.

Instead: talk it through, record the shape in a design note, and file goals only
once the parts that would change the work are settled. A project can sit
`active` with an empty `agent_may` and no goals for as long as this takes. That
is a legitimate state, not a stalled one.

---

## Filing goals

A goal names an outcome and a way to check it. Nothing else.

```markdown
4. **G-004** `obsidian-toby` — Migrate the published vault to GitHub Pages.
   *Done when:* the vault is served from Pages, content is readable by an agent
   over plain HTTP, and the Obsidian Publish subscription can be cancelled.
```

Requirements:

- a **done-when** someone else could check without asking what was meant;
- bounded enough for one `goal-cycle` run, or explicitly marked as a small batch;
- tagged to one `active` project with a non-empty `agent_may`;
- no decision in an `ask` class buried inside it.

Deliberately absent: acceptance-criteria blocks, `Touches` lists, effort
estimates, debriefs. If a goal needs that much ceremony it is Lane B work and
belongs in `task-cycle`.

Score each goal on both axes and say which:

- **Produces something usable** — does it yield a working artifact?
- **Teaches us about working with agents** — does it inform how we build with,
  coordinate, or supervise agents?

High on both is the target. Low on both is the clearest possible drop. High on
one is legitimate — name which one, so the trade-off is explicit rather than
smuggled.

## Project states

| State | Meaning |
|---|---|
| `active` | May receive goals. |
| `parked` | Might resume. Needs a priority decision, not spare capacity. |
| `archived` | Kept for reference. Will not resume without a deliberate restart. |
| `resource` | Read-only source material. Not a work target. |

`agent_may` is a **separate axis** from state. An empty `agent_may` means the
project is alive but human-only — the user works there and agents never schedule
into it. Use it rather than inventing a new state.

Archiving something that is publicly serving requires a closeout pass first:
verify it still works, patch what does not, then archive. Archiving a broken
public page is worse than leaving it active.

Prefer archiving to parking. A parked project is a small standing cost — it
appears in every triage and invites a decision each time. If it has been quiet
for months with no thread back to current work, archive it and note the trigger
that would bring it back.

## Provisional defaults

Agents proceed on reversible decisions rather than blocking. Wasted work is an
accepted cost; nothing is learned from doing nothing. The user ratifies or
overturns at the review.

Reversible means **a git operation undoes it** — including pushing and
deploying. Public projects carry an experimental disclaimer; if someone starts
depending on something they can say so.

Never reversible, therefore never defaulted:

- **package-registry publishes** — crates.io never lets you unpublish, `yank`
  only hides. npm past 72 hours and PyPI are the same;
- spending, third-party contact, publishing under the user's name;
- anything touching secrets, or deleting data with no other copy;
- anything in a `strict`-tier project;
- **what we believe** — findings land provisional; ratification is the user's.

## Unattended execution

Scheduling and delivery are runtime-specific and live in
[`references/hermes-deployment.md`](references/hermes-deployment.md). Nothing in
this skill requires them. A session with no scheduler at all is fully
functional — the queue is worked interactively or by whoever picks it up.

Concurrency rules are in the portfolio repository's `LOCKING.md`: claim the goal,
then take the repo lock, then edit. The clean-worktree check is a safety check,
not a concurrency mechanism.

## Pitfalls

1. **Reviewing without changing anything.** If the queue order never changes, the
   review is theatre. Something should move most weeks.
2. **Filing goals against an unsettled design.** Scope first (§Session B).
3. **Letting the ledger stagnate.** An unchanging `CALIBRATION.md` means the
   system costs the same every week forever.
4. **Reporting only progress.** Say what went badly, or the review loses value.
5. **Parking by default.** Parked projects accumulate and each one costs a
   decision at every triage.
6. **Reintroducing per-project priority.** Rank and attention were priority in
   disguise. Position in the queue is the only priority.
7. **Filling capacity.** Available agent time is not a reason to add goals.
8. **Copying task detail into goals.** The project owns how; the goal owns what.

## Checklist

- [ ] Review covered done, doing, and next, in that order.
- [ ] What went badly was said plainly.
- [ ] Every completion claim was checked against evidence, not reported as told.
- [ ] The queue changed, or there is a reason it did not.
- [ ] New goals have checkable done-whens and are scored on both axes.
- [ ] No goal was filed the user did not agree to.
- [ ] Calibration counts updated; levels moved only on patterns.
- [ ] The attention question (§A5) was asked.
- [ ] Review written to `log/` and committed separately from project work.
