# Debrief: AS-5 Follow the portfolio's retired Blocked section

**Completed:** 2026-09-10
**Commit:** 5fe6ec3

## Design decisions

- **`lifecycle_guard.py` was left alone deliberately.** The brief flagged that
  it needed no code change and that held up under reading: `has_open_claim` is
  `section == "Queue" and claimant is not None and not has_progress`, so a
  blocked goal whose claim has been removed passes from inside the queue. The
  guard also still passes a goal sitting in a `## Blocked` section, which is now
  a representation this repo's skills no longer tell anyone to produce. That is
  intentional tolerance, not oversight — the skills are public and another
  portfolio may still keep one — but it means the guard cannot be used as
  evidence that a portfolio has migrated.
- **A test was added instead of a code change.** The in-queue `*Blocked:*` form
  is now the primary path and had no coverage at all; the section form had a
  test. Without it, a future refactor of `has_open_claim` could break the only
  representation the skills recommend and still pass.
- **The `portfolio-cycle` asset lost the section rather than gaining a stub.**
  An empty `## Blocked` heading in a starter template is an invitation to use
  it. It became an HTML comment above the queue instead, which the template's
  reader sees and a rendered portfolio does not.

## Descoped / deferred

- The asset's `## Not queued, deliberately` section was left as it is. The
  portfolio that motivated this task split that content into its own
  `SCOPING.md` the same day, but the asset is a generic starter and a
  single-file portfolio is a legitimate shape. Revisit if a second portfolio
  outgrows it.
- Whether themes enter the skills at all, and what the three-structures section
  becomes now there are more than three, is a separate portfolio goal awaiting
  the owner's ruling. Nothing here anticipates it.

## Observations

- The public/private boundary check is a pre-commit hook reading Git's index,
  and it rejected the first version of the task file for naming a person. Write
  briefs in this repo referring to *the owner*, not by name, or the filing
  commit bounces.
- This task existed only because a change in another repository made an
  instruction here false. There is no automated link between the two: the
  portfolio's `GOALS.md` and these skills describe the same substrate and drift
  silently. `Depends-on (external)` in the commit trailer is the whole of the
  trace.

## Follow-ups

### Considered and dropped

- Teaching `lifecycle_guard.py` to *reject* a `## Blocked` section outright —
  it would fail portfolios this repo does not own, to enforce a convention that
  is one line of prose.
