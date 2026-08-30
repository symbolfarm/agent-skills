# AS-2: Give the skills a study lane

**Status:** pending · **Priority:** medium · **Blocked by:** none
**Touches:** `skills/work-cycle/SKILL.md`, `skills/portfolio-cycle/SKILL.md`

## Why

The word "study" appears nowhere in any skill. The agreed shape (portfolio
session 2026-08-29) treats study items as **practice on a cadence, not
deliverables in a priority queue** — because ranked against real work they sink
to the bottom permanently, which is the observed fate of two prior attempts at
the same job.

The generator that files these items is filed but unbuilt, so nothing is broken
today. The failure mode is ordering: if the generator lands before the lane
exists, study items file straight into the priority queue and the whole point is
lost on day one. Cheaper to add the lane first.

## Acceptance criteria

1. `work-cycle` recognises a study item as an item type that is **not** selected
   by queue position, and never takes one as "the next eligible item".
2. `portfolio-cycle` reviews the study **rate**, not the study ordering.
3. Both dials are stated with their agreed provisional values: at most
   **3 open** study items, cadence **3 per week**. Written, not implied.
4. The cap is expressed as a refusal condition a generator can check.

## Notes

Values are provisional and review-turnable; record them as defaults, not law.
Do not add a study-specific queue or file — the point is one substrate with a
different selection rule.
