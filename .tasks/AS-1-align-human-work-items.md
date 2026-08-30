# AS-1 — Align the four skills with the agreed human-item model

**Priority:** high
**Blocked by:** nothing
**Depends-on (external):** portfolio G-037
**Touches:** `skills/work-cycle/SKILL.md`, `skills/portfolio-cycle/SKILL.md`, `skills/portfolio-brief/SKILL.md`, `README.md`

## Context

G-034 consolidated six skills into four, but the final pre-execution contract
also said the actionable `OWNER.md` checklist becomes ordinary items with
`assignee: <user>`, while prose may remain in `OWNER.md`. The current skills still
contain transitional language treating OWNER as a separate human queue. The
portfolio migration in G-037 needs the public mechanism to be internally
consistent before its local records and cron jobs are cut over.

## Goal

Make the four-skill documentation consistently describe one merged item view:
portfolio goals are outcomes, repository tasks are implementation, actionable
human work is represented as assignee-marked items, and OWNER is prose/context
rather than a second executable queue.

## Acceptance criteria

- [ ] `portfolio-cycle` no longer instructs reviews or briefs to operate a separate OWNER checklist.
- [ ] `work-cycle` routes discovered user-only unblocks into visible assignee-marked items without inventing strategy.
- [ ] `portfolio-brief` reports assignee-marked items from the merged queue.
- [ ] README describes `work-cycle` and the unified execution/research model.
- [ ] Historical/legacy references remain explicitly historical rather than being rewritten.
- [ ] Frontmatter checks, public-boundary hook, and `git diff --check` pass.

## Relevant files

- `skills/work-cycle/SKILL.md`
- `skills/portfolio-cycle/SKILL.md`
- `skills/portfolio-brief/SKILL.md`
- `README.md`

## Decisions already made

- G-034 final pre-execution contract (`portfolio` commits `72b5a1b` / `028b24a`) is authoritative.
- Involvement stays in `CALIBRATION.md` by decision class; do not add auto/report/ask to items.
- `OWNER.md` may retain prose, but not an executable checklist outside the merged queue.
- `portfolio-brief` remains the light recurring entry point; `portfolio-cycle` does not split.

## Out of scope

- Re-ranking real portfolio work.
- Editing the private portfolio repository in this task.
- Changing Hermes cron configuration.
