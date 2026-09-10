# AS-5 Follow the portfolio's retired Blocked section

**Blocked by:** nothing
**Touches:** `skills/work-cycle/SKILL.md`, `skills/portfolio-cycle/assets/GOALS.md`

## Context

G-090 removed the `## Blocked` section from the portfolio's `GOALS.md` on
2026-09-10. It had stood empty since 2026-08-26, and the parser already
supported a `*Blocked:*` line on a goal that keeps its queue position — so the
section was a second representation of the same state, and a third place (after
`COMPLETED.md` and `archive/queue-rationale.md`) for an item to leave the queue
and stop being re-ranked.

`work-cycle` still instructs a lane to *move it to `Blocked`*. Following that
instruction now recreates the section the portfolio just retired, and puts the
blocked goal somewhere nobody re-ranks. This task is the downstream repair of a
change already landed, not a new proposal.

`lifecycle_guard.py` needs no code change: a blocked goal that has had its claim
removed has no open claim, so it passes from inside the Queue section.

## Goal

The skills say what the portfolio now does: a blocked goal stays in the queue,
at its position, carrying a `*Blocked:*` line.

## Acceptance criteria

- [ ] `skills/work-cycle/SKILL.md` "User-blocked goal" step 2 keeps the goal in
      the queue with a `*Blocked:*` line naming what is needed, who owns it, and
      the date
- [ ] The run-exit-gate paragraph's "A goal in `Completed` or `Blocked`" wording
      matches the new representation
- [ ] `skills/portfolio-cycle/assets/GOALS.md` drops its `## Blocked` section
      and documents the line instead
- [ ] `python3 -m pytest tests` (or the repo's runner) passes

## Out of scope

Whether themes enter the skills, and what the three-structures section becomes —
that is a separate portfolio goal, and the owner's ruling.
