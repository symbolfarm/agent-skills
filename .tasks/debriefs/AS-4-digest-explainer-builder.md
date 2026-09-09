# Debrief: AS-4 Point digest at the standard-library explainer builder

**Completed:** 2026-09-10
**Commit:** fcf58e9

## Design decisions

Named the reference implementation by repository-relative path rather than an absolute workspace path so the public skill does not encode one installation layout. The instruction preserves established project substrates; G-087 selected a common fallback and convention, not a forced migration.

## Descoped / deferred

The builder implementation and real-fixture trial remain in external portfolio goal G-096 and land in `adus-intelligence` after this task. The skill text describes that approved contract but does not duplicate its full configuration schema.

## Observations

The skill already delegated declaration details to a calling project's page convention. The new substrate paragraph therefore only needs to settle renderer choice and reproducibility behavior; repeating `EXPLAINERS.md` would create two maintained contracts.

## Follow-ups

### Considered and dropped

- Copying the builder into the skill repository — rejected because the public ADUS repository must remain independently buildable in CI, and two copies would drift.
