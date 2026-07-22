# Project portfolio

> Start here for cross-project planning. `PROJECTS.json` is the registry and
> policy source; each project repository remains authoritative for its tasks,
> research, and completion state. Use the `portfolio-cycle` skill for planning
> and reconciliation.

## Current attention

<!-- Summarize the primary and secondary projects after each evening plan. -->

No attention order has been approved yet.

## Today's plan

No frozen plan yet. See `plans/`.

## User agenda

See `DECISIONS.md` for open decisions and reviews.

## Operating rhythm

1. Evening: inspect deltas, resolve user-gated items, set attention, and freeze
   tomorrow's bounded plan.
2. Daytime: cron jobs execute one project-local packet per fresh session,
   commit locally, and never push.
3. Reconciliation: verify project evidence and write `reviews/YYYY-MM-DD.md`.

## Authority map

| Concern | Authority |
|---|---|
| Project membership and automation policy | `PROJECTS.json` |
| Daily selection and ordering | `plans/YYYY-MM-DD.json` |
| User decisions and reviews | `DECISIONS.md` |
| Task definitions and status | each project's `.tasks/` |
| Research understanding | each project's `notebook/` |
| Actual work delivered | project Git history and debriefs |
| Daily cross-project outcomes | `reviews/YYYY-MM-DD.md` |
