---
name: goal-cycle
description: >-
  Execute one goal from the portfolio queue. Claim it, lock the repository, do
  the work, take provisional defaults on reversible decisions, log what was
  decided, and leave a way for the user to try the result. Use when working the
  build lane — unattended or interactively — and whenever asked to "take the
  next goal". Deliberately lighter than task-cycle: no briefs, no acceptance
  criteria, no debriefs.
license: MIT
metadata:
  author: Symbol Farm
  version: "1"
  category: productivity
  tags: portfolio, goals, execution, build-lane
---

# Goal cycle

Execution for the build lane. One goal per run.

The artifact is the record. Git history is the debrief. This skill exists to
keep the loop honest — claim before working, decide rather than block, log what
was decided, and hand back something the user can actually try.

**Use `task-cycle` instead** for research-lane work, where the decisions are
low-level, the user stays involved, and a durable task record earns its weight.

## The loop

### 1. Choose

Read `GOALS.md` in the portfolio repository. Take the **highest-priority
unclaimed, unblocked** goal. Position is priority — do not re-rank, and do not
skip a goal because a later one looks easier.

> **Portfolio location.** These skills assume one portfolio repository holding
> `GOALS.md`, `PROJECTS.json`, `CALIBRATION.md`, `OWNER.md` and `log/`. Point
> them at wherever yours lives; the reference deployment uses
> `/workspace/portfolio`.

Check `PROJECTS.json`: the goal's project must be `active` with a non-empty
`agent_may`. If it is not, stop and report — the queue and registry disagree,
and that is worth surfacing rather than working around.

**Capability skip.** If the project declares `requires`, verify your
environment provides each capability *before* claiming. If it does not, skip to
the next goal and **name the skipped goal and the missing capability in your
report**.

This is the only permitted exception to "do not skip a goal", and it is narrow
deliberately: skip only for a declared, objectively checkable capability your
environment lacks — a GPU, a framework, a network route. Never for difficulty,
length, or preference. The report is what keeps it honest; a skip nobody sees
is indistinguishable from cherry-picking.

A skipped goal is **not blocked**. It keeps its position, stays unclaimed, and
waits for an agent that can run it. Do not move it to `## Blocked`, and do not
file anything in `OWNER.md` — nothing is required of the user.

Read `CALIBRATION.md` before starting, not after a decision is already made.

### 2. Claim

Add a `*Claimed:*` line with agent and timestamp, then **commit it**. Claiming
is a commit so races resolve as conflicts rather than as two agents doing the
same work.

Claim first, then work. Never work then claim.

### 3. Lock

Take `.tasks/.lock` in the project repository, per the portfolio's `LOCKING.md`.
If another agent holds a live lock, release the claim and report a no-op — do
not wait.

Order is always: claim the goal, then take the repo lock, then edit.

### 4. Work

Do the thing. Follow the project's own conventions: read its `AGENTS.md` or
`CLAUDE.md`, match the surrounding code, run its tests.

Commit as you go at natural boundaries. Small commits are the record.

### 5. Release

Release the lock. Update the goal — done, or still in flight with what remains.
Write the log entry. Commit the portfolio change separately from project work.

### Deployment barrier before removing push authority

If completing a goal will archive a project, clear its `agent_may`, or otherwise
remove the mechanism that publishes its commits, verify the project branch is
already at remote parity **before** making that state transition. When the
done-when includes deployment, also verify the deployed artifact rather than
inferring deployment from a local commit.

If commits are still ahead of the remote, leave the project active and the goal
in flight with a progress note such as `awaiting publish, then verify and
archive`. Return `partial`. Never archive first and expect an active-project
pusher to publish afterward: removing push authority can strand the very commit
that justified the closeout.

## Resuming an interrupted goal

Runs get cut off — usage limits, crashes, a closed laptop. Assume it will
happen rather than designing as though it will not.

**Stopping on purpose:** update the claim line with where you got to, then
commit it.

```markdown
   *Claimed:* claude, 2026-08-05T14:22+09:30
   *Progress:* pages audited, three broken links fixed. Next: the canvas sizing
   on maze.html, which fails below 400px.
```

One line. It lives where the next agent already looks, and it carries the one
thing the artifact cannot: what you were about to do.

**Stopping without warning:** you write nothing, so the commits are the record.
This is why `goal-cycle` commits at natural boundaries rather than once at the
end — frequent commits are what make an ungraceful death recoverable.

**Picking up a claimed goal.** If the top goal is already claimed:

1. **Claimed by you, lock still held** — resume. Read the progress note, then
   `git log` since the claim timestamp to see what actually landed.
2. **Claimed by you, lock released after a deliberate partial result** — this is
   the normal next-run path. Confirm the project worktree is clean, reacquire the
   lock, read the progress note and commits, and resume the same goal. Do not skip
   to the next unclaimed goal merely because the prior run released its lock.
3. **Claimed by another agent, lock live** — leave it. Take the next goal.
4. **Claim older than 24 hours, lock expired** — it was interrupted. Read the
   progress note and the commits since the claim, re-claim it under your own
   name, and note in `log/` that you took over. Never silently adopt a claim.
5. **Claimed, but no commits and no progress note** — nothing was done. Re-claim
   and start fresh.

Reconstruct from the done-when, not from a guess at the previous agent's plan.
The done-when is the contract; how it gets met is open.

If resuming would mean redoing more than it would to restart, restart — and say
so in the log.

## Deciding rather than blocking

When a decision blocks progress, **take the default and keep going**. Record it.
The user ratifies or overturns at the review. Wasted work is an accepted cost;
nothing is learned from doing nothing.

Check the class in `CALIBRATION.md` first:

| Level | Do |
|---|---|
| **auto** | Decide, proceed, do not log it. |
| **report** | Decide, proceed, log it with the reasoning. |
| **ask** | Stop. Do not decide. Record what is needed and move on or halt. |

If the class is not in the ledger, treat it as **report**, log the decision as
`unclassified`, and describe what kind of decision it was. **Do not invent a
class name.** Only a `portfolio-cycle` review creates classes or moves levels;
a run that mints its own leaves the ledger with rows nobody agreed to and
counts that never accumulate.

### Reversible means a git operation undoes it

Including pushing and deploying. Public projects carry an experimental
disclaimer; if someone starts depending on something they can say so.

Never reversible, therefore never defaulted, regardless of ledger level:

- **package-registry publishes** — crates.io never lets you unpublish, `yank`
  only hides it. npm past 72 hours and PyPI are the same;
- spending, or metered provider cost at scale;
- third-party contact — email, issues on other people's repos, posts;
- publishing under the user's name to a venue with a public edit history;
- anything touching secrets, or deleting data with no other copy;
- **anything at all in a `strict`-tier project**;
- **what we believe** — that is the research lane's, and it is the user's.

When one of these is in the way, that is a genuine block. Say so and stop.

## When the block is the user's, demote the goal

A goal blocked on the user must not stay at the head of the queue. Holding the
claim there costs a run every cycle, produces nothing, and starves everything
behind it. The user comes back to these in their own time, which is often days.

So when a run establishes that a goal cannot proceed without the user:

1. **Release the claim.** Delete the `*Claimed:*` line. A blocked goal is not
   in flight and should not look like it.
2. **Move the entry to the `## Blocked` section** of `GOALS.md`, keeping its
   `G-NNN` identifier, and add a `*Blocked:*` line naming what is needed, who it
   is on, and the date.
3. **File the unblock in `OWNER.md`**, under the heading it belongs to, naming
   the goal it blocks. That file is where the user looks; the queue's `Blocked`
   section is where agents look.
4. **Take the next eligible goal in the same run.** A block is not a reason to
   end the run.

```markdown
- **G-014** `example-tool` — Clear the dependency alerts.
  *Done when:* …
  *Blocked:* needs the authenticated vulnerability-alert list; the scheduled
  environment has no forge credentials (401). On the owner, 2026-03-09.
```

Restoring a demoted goal to the queue is a **priority decision**, made at a
`portfolio-cycle` review once the block clears — not automatically by the next
run that notices it is unblocked. Position on return is the user's to choose.

**Distinguish this from a partial result.** Partial means the work is real and
resumable by an agent — keep the claim, add a `*Progress:*` line, resume next
run. Blocked means no agent run can advance it. Two runs producing the same
"still blocked" note is the signal that a partial was really a block.

## Stopping

Stop and report when:

- the goal's done-when is met;
- an `ask`-class or irreversible decision is required;
- the goal turns out to be much larger than one run — say what it actually is;
- the done-when is ambiguous enough that two people would disagree on it;
- another agent holds the lock;
- the registry and queue disagree.

**A no-op is a correct result.** Never substitute unrelated work because the
chosen goal did not pan out — that hides the fact that the queue needs
attention. A goal *demoted* to `Blocked` is the exception rather than a
substitution: the queue moved, so continuing to the next goal is correct.

Partial progress is fine and normal. Leave the goal claimed only if resuming
soon; otherwise release the claim and say what remains. If what remains is the
user's, demote it rather than leaving it claimed.

## Logging

Append to `log/YYYY-MM-DD.md` in the portfolio repository:

```markdown
## G-002 `puzzle-site` — closeout pass

**Result:** done / partial / no-op / blocked
**Commits:** 4 in puzzle-site
**Try it:** https://example.github.io/puzzle-site/ — the maze on the landing
page was not loading; it is the quickest thing to check.

**Decisions**
- *dependency-choice (report):* dropped the unused analytics script rather than
  updating it — nothing referenced it.
- *public-copy (report):* reworded two error messages that referenced a dead URL.

**Weakest point:** only checked in Firefox. The canvas sizing is the most likely
thing to differ elsewhere.
```

Two parts are not optional:

**Try it** — a command, path, or link. Where a goal produced something the user
could experience, hand over the way in rather than describing it. Judging a
summary is expensive and inaccurate; using the thing takes a minute and is
accurate. For work that is understood rather than run, prefer a pinned visual —
a mermaid diagram or self-contained HTML page.

**Weakest point** — the part you would attack if reviewing this. One clause. It
is cheap to produce and falsifiable: confidence that later proves misplaced is
calibration evidence. Omit only when there genuinely is nothing; do not
manufacture false modesty, and do not let it become boilerplate.

## What this skill deliberately does not have

No task briefs. No acceptance criteria beyond the goal's done-when. No
`Touches` lists. No debriefs. No effort estimates.

Debriefs exist to hand context between agents. Here the artifact is the record
and the commits are the trail. If a piece of work genuinely needs that
machinery, it is research-lane work and belongs in `task-cycle`.

Resist adding ceremony here. The weight of this skill is a feature.

## Pitfalls

1. **Working before claiming.** The claim is what makes the queue safe for more
   than one agent.
2. **Re-ranking the queue.** Position is priority and it is the user's. Take the
   top one.
3. **Blocking on a reversible decision.** Take the default, log it, keep going.
4. **Defaulting on an irreversible one.** Check the list above every time.
5. **Logging `auto` decisions.** The ledger exists so the record gets shorter.
6. **Describing the artifact instead of handing it over.** Give the way in.
7. **Substituting work.** A no-op is correct; unrelated work is not.
8. **Silent scope growth.** If the goal is bigger than it looked, say so rather
   than quietly working for hours.
9. **Leaving a user-blocked goal claimed at the head of the queue.** It costs a
   run every cycle and starves everything behind it. Demote it and continue.
10. **Inventing a calibration class.** Log it `unclassified`; the review names
   it.
11. **Touching a `strict` project.** A `strict`-tier project takes no provisional
   defaults at all.

## Checklist

- [ ] Goal was the top unclaimed, unblocked entry.
- [ ] Project is `active` with a non-empty `agent_may`.
- [ ] Claim committed before any work started.
- [ ] Repo lock taken, and released on every exit path.
- [ ] No irreversible action taken without asking.
- [ ] Decisions logged at the level `CALIBRATION.md` specifies.
- [ ] A project was not archived or stripped of push authority while required
  commits were still ahead of its remote.
- [ ] Log entry has a **Try it** and a **Weakest point**.
- [ ] Portfolio changes committed separately from project work.
- [ ] Goal marked done, or its remainder stated plainly.
- [ ] A goal blocked on the user was demoted to `Blocked`, its claim released,
  the unblock filed in `OWNER.md`, and the next goal taken.
- [ ] No new calibration class was invented; unfamiliar decisions logged
  `unclassified`.
