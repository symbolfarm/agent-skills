# Debrief: AS-1 Align the four skills with the agreed human-item model

**Completed:** 2026-08-30
**Commit:** 2786a62

## Design decisions

- Treated `Yours` as a filtered view over assignee-marked items rather than a second source record.
- Kept `OWNER.md` available for standing prose, while removing instructions that made it an executable checklist.
- Allowed agents to create a user-assigned unblock only as transcription of a requirement created by already-approved work; this preserves the no-speculative-goals boundary.
- Kept decision briefs as an optional artifact but removed build-lane/research-lane execution language.

## Descoped / deferred

Private portfolio records, queue rendering, and scheduler migration remain in portfolio G-037.

## Observations

The public-boundary hook caught a personal name in this task brief after the initial local filing commit. The local-only task commits must be rewritten before publication so the protected term does not enter public history.

## Follow-ups

### Filed as tasks

None.

### Considered and dropped

- A per-item `auto/report/ask` field remains rejected because it would duplicate the calibration ledger and would not accumulate evidence by decision class.
