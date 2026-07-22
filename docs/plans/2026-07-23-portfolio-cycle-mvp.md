# Portfolio-cycle MVP plan

Date: 2026-07-23
Status: implemented as a first draft

## Goal

Add a portable `portfolio-cycle` skill and bootstrap a companion
`/workspace/project-portfolio` repository. The portfolio selects work across
projects while each project remains the authority for its own task and research
cycles.

## MVP decisions

- Keep the public `agent-skills` repository as the canonical skill source.
- Use JSON for the project registry and daily plans so validation needs only the
  Python standard library.
- Keep decisions/reviews in Markdown because they are conversational artifacts.
- Treat a frozen daily plan as immutable input to cron jobs; record outcomes in
  a separate daily review to avoid concurrent plan writes.
- One work packet targets one project and one filed task.
- Cron jobs commit locally but never push.
- Seed discovered repositories conservatively: known GNN projects are active;
  other repositories are candidates until the user triages them.

## Deliverables

- `skills/portfolio-cycle/SKILL.md`
- portable registry, plan, decisions, review, and dashboard templates
- a standard-library validator and tests
- `/workspace/project-portfolio` initialized as its own Git repository
- an initial registry populated from current `/workspace` repositories

## Verification

- validate all skill frontmatter and supporting-file discovery
- run validator unit tests
- run the validator against the initialized portfolio
- load `portfolio-cycle` through Hermes
- commit each repository independently; do not push
