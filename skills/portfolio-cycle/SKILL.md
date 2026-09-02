---
name: portfolio-cycle
description: >-
  Run the interactive portfolio session: a twice-weekly review of what got done,
  what is in flight, and what comes next; re-order the single goal queue; update
  project states and the calibration ledger; teach the state of a research
  project in depth; and turn agreed direction into allocated goals and tasks.
  Use when the user asks for a review, wants to learn or set direction, wants to
  set or re-order goals, or wants to change a project's state or trust level.
  Repository state is evidence; the conversation is the source of strategy.
license: MIT
metadata:
  author: Symbol Farm
  version: "9"
  category: productivity
  tags: portfolio, review, goals, planning, multi-project
---

# Portfolio cycle

The interactive session where direction is set. Runs against the portfolio
repository, works with no scheduler present, and needs nothing from any
particular agent runtime.

> **Portfolio location.** These skills assume one repository holding `GOALS.md`,
> `PROJECTS.json`, `CALIBRATION.md` and `log/`. It may also keep an `OWNER.md`
> for standing prose and context, but executable user work belongs in the merged
> item queue rather than a second checklist. Point the skills at
> wherever yours lives; the reference deployment uses `/workspace/portfolio`.

`portfolio-brief` reports between sessions. `work-cycle` executes. This skill is
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
- Keep task-level detail in the project. A goal names an outcome; `work-cycle`
  decides how and manages implementation tasks.
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
- anything that turned out differently from what was expected;
- **the user's filtered queue view**: from the same merged item queue, count
  items whose `assignee` is the user, identify which block a goal and which are oldest,
  and — the part that takes actual thought — which one is most worth the user's
  attention this week. Come with a recommendation, not an inventory.

Compress hard. The user should not have to reconstruct context. Name artifacts
they can open, not commits they would have to read.

### A2. Present

Four headings, in this order, and nothing else:

**Done** — what actually landed, with what to try. Two or three items, grouped.
**Doing** — what is in flight, and anything stalled with the reason.
**Next** — the current top of the queue, as a proposal to react to.
**Yours** — the assignee-filtered user items, ranked, with the top one or two put forward as
decisions to make *now*, in this session.

Say plainly what did not go well. A review that only reports progress stops
being useful within a month.

#### Why "Yours" is a heading and not a second queue

The first three headings are all about agent work, which is the half that
already moves on its own. A review made only of those reports on the part of
the system that is not stuck.

These items live in the same source records and derived view as agent work;
`Yours` is only a filter for attention. **The review is the one moment the user
is reliably present.** That is what it
is for. If their queue is not put in front of them here, the only remaining
mechanism is that they remember to open a file — and remembering to open a file
is not a mechanism, it is a hope.

So: rank the items, say which you would do first and why, and drive at least one
to an actual decision before the session ends. Ranking is the part that helps
most. A user short on time and energy is not helped by a list; they are helped by
someone saying *this one, now, it takes ten minutes, here is what you need to
know to decide it.*

Do not let this become a full read-out of the backlog. One or two, chosen and
argued for. The rest stay in the file.

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
- **Close or advance at least one user-assigned item**, and record the
  outcome. "Discussed" is not an outcome; decided, done, reshaped, deferred with
  a date, or dropped are. An item that survives a review untouched three times
  running is evidence the review is not doing this job.
- Write the review to `log/YYYY-MM-DD-review.md`.
- End by allocating the agreed work to both parties: goals and agent-authored
  implementation tasks for agents; queue items with `assignee: <user>` for the
  user's work. Do not leave either side as an implied checklist in prose.
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

## Research depth mode: learn, then plan

When a review touches a research project and the user asks to get up to speed,
decide what the evidence means, or plan the next experiment, deepen the ordinary
review rather than invoking a separate research cycle.

### Learning

1. Find the most recent learning entry in `notebook/log/`; if none exists,
   orient from `notebook/INDEX.md`.
2. Assemble the delta: changed notes and experiments, new lab-log entries,
   completed-task debriefs, and implementation changes that bear on theory.
3. Walk the delta as a conversation, most significant finding first. Do not
   dump a report. Stress the load-bearing notes: ask why a result occurred, what
   would falsify it, and which assumption carries the next decision.
4. Repair notes when explanation exposes ambiguity or staleness. Explanation
   failure is a note-quality test, not something to talk around.
5. Converge on a direction with the user. Record a `Session — learning` entry
   ending in a **Direction** block, including the important alternatives not
   taken, and update `INDEX.md` if open questions changed.

The output is a user who can state the project's position in their own words,
plus a written direction. What the research record says we believe is never a
provisional agent default; the user ratifies it.

### Planning and allocation

With a direction agreed, decompose it in conversation. Goals express outcomes
and are authored by the user in this review. Tasks express implementation and
are authored by an agent under `work-cycle`. This is an outcome/implementation
axis, not a size axis.

For each experiment task, pre-register a notebook experiment stub with
Hypothesis and Setup drafted and `verdict` unset. Link the relevant notebook
notes from the task brief so a cold-starting agent inherits the theory. File the
tasks and dependency order through `work-cycle`, and update the Direction entry
with the IDs it spawned.

Do not add an involvement field to goals or tasks. Human involvement is decided
per decision class in `CALIBRATION.md`, where evidence can accumulate.

---

## Filing goals

A goal names an outcome and a way to check it. Nothing else.

```markdown
- **G-004** `notes-vault` — Migrate the published vault to static hosting.
  *Done when:* the vault is served from the static host, content is readable by
  an agent over plain HTTP, and the paid publishing subscription can be
  cancelled.
```

Requirements:

- a **done-when** someone else could check without asking what was meant;
- bounded enough for one `work-cycle` run, or explicitly marked as a small batch;
- tagged to one `active` project with a non-empty `agent_may`;
- no decision in an `ask` class buried inside it.

Use unnumbered bullets. The stable `G-NNN` identifier is the goal's identity;
physical position is priority. Removing or moving a goal must not require
renumbering the rest of the queue. When a goal delegates its implementation to
an already-filed repository task, add `Implements: <task-id>` so the merged view
and `work-cycle` follow that task's live lifecycle instead of creating a duplicate.

Add `Blocks:` naming the goals or repository tasks that cannot proceed until
this goal lands — e.g. a later goal gated by this result. It is a **derived-view
field, not a second queue**: queue position still carries priority, and `Blocks:`
only lets the brief and review say *why* an item sits where it does. `work-cycle`
must not re-rank or select on it, and `portfolio-brief` reports it as gating.

Deliberately absent: acceptance-criteria blocks, `Touches` lists, effort
estimates, debriefs. If implementation needs that machinery, file project tasks
and execute them through `work-cycle`.

### User-assigned items

Do not keep the user's executable work as checklist bullets hidden in prose.
Represent it in the same merged queue substrate with `assignee: <user>` and a
`Created` date so the brief can report age. Add `Requires: computer` when it
needs a desk; those items are raised in the interactive review. Items without
that requirement may be routed through the recurring brief. The requirement
field has the same capability-routing meaning for users and agents—do not invent
a second routing concept. A user item may carry `Blocks:` naming what it gates;
this is why a review or brief can surface *one* user item ahead of others (see
`portfolio-brief`'s "User-assigned items"). It remains a derived-view field, not
a second queue.

The user normally authors outcome items during a review. An agent may add a
user-assigned item only when it is transcribing work the user stated or making a
mechanically necessary unblock from an already-approved goal visible. That is
not permission to invent speculative work or choose strategy on the user's
behalf. Keep standing commitments and explanatory material as prose; only an
executable action becomes an item.

### Shape, not size

Do not estimate effort. Hours are guesses that become theatre, and the queue
does not need them.

Do judge **shape**, because a queue cannot be ordered without it:

| Shape | Sign | What to do |
|---|---|---|
| **One run** | The work is understood and bounded. | File it. |
| **Look first** | Nobody knows what the work is until someone looks. | File the *reconnaissance* as the goal. |
| **Programme** | Several goals wearing one name. | Split it, or scope it (§Session B). |

The failure this prevents: a goal everyone agrees is important but nobody can
place, because its size is unknown. That is not a priority problem, it is a
missing-information problem, and reconnaissance is cheap.

A worked example. *"Patch the dependency vulnerabilities"* in one small tool
looked like days of work and sat unplaceable for weeks. Ten minutes of actually
looking established where the alerts lived, which of them the tool's own usage
could even reach, and that refreshing the lock file cleared the bulk of them. It
became a short goal plus one release decision — orderable, and much smaller than
feared.

Note what the reconnaissance produced besides an estimate: findings about a
security posture. Keep those in the private portfolio. A public skills
repository is the wrong place to record which of a project's vulnerabilities
were judged not worth fixing.

**When you cannot tell whether a goal is one run, the first goal is the
reconnaissance.** It turns missing implementation knowledge into one bounded,
checkable outcome instead of disguising uncertainty as an estimate.

### Not everything worth doing is a goal

Some work is a decision before it is a task. A website that needs its purpose
settled, a rename, a restructure — filing these as goals produces motion without
direction.

If the question "what would done look like?" cannot be answered in a sentence,
it is a scoping conversation (§Session B), not a queue entry.

Equally, resist goals that exist only to complete a policy. If nobody is
affected by the gap, closing it is make-work — file it when something else
brings you into that repository anyway.

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

## Changing the process

These skills and the portfolio's conventions are ours to edit, and the review
session is where that happens. Where the evidence lives, and what may not
change itself.

**`CALIBRATION.md` is the register.** Process hypotheses do not get their own
file. A separate register accumulates one instance per row, which is a sample
size that never moves a level — the portfolio kept one from 2026-07 to 2026-08
and retired it without a single row graduating. The ledger works because it is
keyed by decision class and every run feeds it.

**The self-review boundary.** A review may inspect anything — logs, decisions,
goal outcomes, runtime, how much steering the user had to supply — and may
propose changes. It may not, on its own initiative, rewrite its governing skill,
change strategic priority, mutate an agreed plan, expand unattended authority, or
treat more automation as self-evidently better. Propose; the user rules.

**Reject an improvement that** mainly adds ceremony, optimises a rare edge case,
creates reporting nobody reads, measures activity instead of decision quality, or
moves strategy from the user into automation. Changing something promptly is
right when current behaviour is unsafe, can execute unintended work, documents a
command or API that is wrong, or makes the workflow impossible. Everything else
waits for a repeated pattern.

## Pitfalls

1. **Reviewing without changing anything.** If the queue order never changes, the
   review is theatre. Something should move most weeks.
2. **Filing goals against an unsettled design.** Scope first (§Session B).
3. **Letting the ledger stagnate.** An unchanging `CALIBRATION.md` means the
   system costs the same every week forever.
4. **Reporting only progress.** Say what went badly, or the review loses value.
5. **Treating user-assigned items as out of scope.** The three original headings
   covered agent work only, which is the half that already moves. If the review
   never puts the user's own decisions in front of them, the queue's sole
   remaining mechanism is their memory — and a queue defended by memory is a
   queue that grows. Filter the merged view, rank the user-assigned items, and
   land one.
6. **Explaining a stalled item as "mis-shaped" when it is simply neglected.**
   Reshaping is sometimes right, but reaching for it first is a way of sounding
   thoughtful while letting a backlog rot. Ask the user which it is; they know,
   and their answer beats the inference. Time and energy are finite and that is
   not a defect in the item.
7. **Parking by default.** Parked projects accumulate and each one costs a
   decision at every triage.
8. **Reintroducing per-project priority.** Rank and attention were priority in
   disguise. Position in the queue is the only priority.
9. **Filling capacity.** Available agent time is not a reason to add goals.
10. **Copying task detail into goals.** The project owns how; the goal owns what.
11. **Re-explaining the same research confusion.** Rewrite the note that keeps
    failing instead of spending another session narrating around it.
12. **Batch-repairing a stale notebook index.** Repeated drift means execution
    is skipping its findings distill; fix that close-out habit.
13. **Refining briefs when direction is ambiguous.** Return to learning and
    settle the question with the user before producing more implementation text.
14. **Leaving the user's work in prose.** Allocate it as assignee-marked items so
    the merged queue and recurring brief can see it.

## Checklist

- [ ] Review covered done, doing, and next, in that order.
- [ ] What went badly was said plainly.
- [ ] Every completion claim was checked against evidence, not reported as told.
- [ ] The queue changed, or there is a reason it did not.
- [ ] New goals have checkable done-whens and are scored on both axes.
- [ ] No goal was filed the user did not agree to.
- [ ] Calibration counts updated; levels moved only on patterns.
- [ ] The attention question (§A5) was asked.
- [ ] At least one user-assigned item was closed, advanced, or explicitly dropped.
- [ ] Agreed next work was allocated to both agents and the user as actual items.
- [ ] Review written to `log/` and committed separately from project work.
