# Delegation

The lead agent stays responsible for everything that reaches `main`.
Delegation buys parallel work and a second pair of eyes. It does not move
accountability.

## What to delegate

Good delegation units have a stated interface and a check that can judge the
result without the lead redoing the work:

- an extension built against a written contract (a plugin, a game, a report type);
- a module behind an existing interface;
- a review of a branch, a design or the document pack;
- a playtest or usage pass on a build, from its instructions alone;
- a security scan and triage;
- a polish judgement against the rubric.

Keep with the lead: what to build next, product taste, and changes to
contracts or architecture. Keep with the lead, too, any decision the brief
reserved for the owner.

## The brief

Write each delegated task as a self-contained brief. The other agent has none
of your context.

- **Goal:** what the recipient gains.
- **Interface:** the contract, files or API it must work through, and what it
  must not touch.
- **Done:** the checks that must pass, the evidence to return (test output,
  screenshots), and the time or token limit.
- **Return:** a branch or patch, plus a short note of decisions made and open
  issues.

## Isolation

Give each delegated builder its own branch or worktree from current `main`.
Never let two agents write the same working tree. Reviewers and judges read
and do not write.

## Agents from another vendor

An agent from another vendor can be run non-interactively through its
command-line interface (for example `codex exec "<brief>"`, run in the task's
worktree) for building, or through its review command for a review. Check
the CLI is installed and authenticated with a version call before relying on
it. Different models catch different problems, so cross-vendor review is
worth its cost on significant merges. Record which agent and model did each
task in `DECISIONS.md` and the scorecard. Comparing agents across builds is
part of what a build teaches.

## Reviewing delegated work

Before merging, the lead reads the diff and the returned evidence and re-runs
the checks. A delegated change goes through the same verification as the
lead's own, including the first-touch gate when it changes anything a user
touches. When review findings and the author disagree, the lead decides and
records why.

## Alternation

For a significant change, the agent who wrote it should not be the only one
to judge it. A useful rhythm is builder → reviewer → builder fixes → merge,
with the roles held by different agents, or by fresh contexts of the same
agent when no other is available.
