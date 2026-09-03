# Debrief: AS-3 Draw the goal-line / ledger boundary

**Completed:** 2026-09-03
**Commit:** d9f0dda

## Design decisions

The boundary was added during G-062 rather than as an isolated wording pass
because the migration was already reconciling shared goal, queue, and decision
semantics across the skill family. The wording keeps implementation opinions as
constraints on one outcome and reserves involvement levels for the calibration
ledger.

## Descoped / deferred

Nothing descoped.

## Observations

The same audit found a second semantic collision: repository task records still
carried a high/medium/low priority field even though JSONL order is the task
selection order. G-062 removed that competing field while preserving record
order and Git history as the audit trail.

## Follow-ups

### Considered and dropped

- A new per-goal involvement field — it would duplicate calibration classes and
  recreate the ambiguity AS-3 was filed to remove.
