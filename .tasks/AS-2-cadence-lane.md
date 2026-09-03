# AS-2: Give the skills a cadence lane

**Status:** pending · **Blocked by:** none
**Touches:** `skills/work-cycle/SKILL.md`, `skills/portfolio-cycle/SKILL.md`

## Why

Some work is a **habit, not a deliverable**. Ranked by queue position against
real work it sinks to the bottom permanently — the observed fate of two prior
attempts at comprehension, and of a one-session X post that survived three
briefs at the top of a list.

Position-is-priority is right for outcomes and wrong for practice. Practice needs
a **rate**.

Two kinds of work have this shape, and they are the same shape:

- **Study** — active-recall items over a codebase, so the user can check what
  agents built rather than trust a summary of it.
- **Cleanup** — dead code, drift, comprehension debt. The most recent such item
  in this workspace was filed only because an agent happened to notice it while
  writing something unrelated. That is luck, not a system.

Generalised from "study lane" to "cadence lane" on 2026-08-30: cleanup does not
want its own skill. A `cleanup-cycle` would be `work-cycle` with a different
mood, and the skills went 6 → 4 that morning on exactly that principle. What
cleanup shares with study is not its execution — it is that both arrive on a rate
and neither survives priority ordering.

## Acceptance criteria

1. `work-cycle` recognises cadence items as a class that is **not** selected by
   queue position, and never takes one as "the next eligible item".
2. `portfolio-cycle` reviews the **rate**, not the ordering.
3. Dials stated with their agreed provisional values: at most **3 open** items,
   cadence **3 per week**. Written, not implied. Review-turnable.
4. The cap is expressed as a refusal condition a generator can check.
5. The lane admits more than one generator — study and cleanup ride the same
   mechanism and are distinguished by what files them, not by how they run.

## Notes

Do not add a separate queue or file: one substrate, a different selection rule.
Do not add a skill. Study's generator is already filed as a portfolio goal;
cleanup has no generator yet and does not need one for this task — the lane must
simply not assume a single source.
