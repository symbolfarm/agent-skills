---
name: product-cycle
description: Build a polished, production-ready software product to a set budget, leading a team of agents, keeping main shippable at every merge, and handing over a document pack that lets a person use and develop what was built. Use for authorized product builds of any size, from a 30-minute hackathon slice to a multi-run build.
license: MIT
metadata:
  version: "1"
---

# Product cycle

A product build is judged by what its recipient gets: something that works
when they first touch it, feels finished, and comes with documents that let
them use it and change it. Meeting the minimum requirements is where the build
starts, not where it stops. The build keeps improving the product until the
budget is spent, unless the next improvement is not worth making.

Under a charter, `charter-cycle` still owns claims, requirement lifecycle,
close-outs and reports. This skill owns how the product is built. For a direct
request, the request is the authority and its stated budget is the budget.

## Budget and authority

The budget is set when the work is authorized: minutes, hours, runs, tokens or
spend, in any combination. It can be as small as 30 minutes. Read it first and
plan to it. Never extend it yourself.

Within the brief, the lead agent has licence to decide what to build, how, and
in what order. That includes features the brief did not list, when they serve
its purpose. Record every consequential choice in `DECISIONS.md` (see
[document pack](references/document-pack.md)). Where a choice is a real fork
(a rendering approach, a data model, a reward rule, a vendor), put each side
behind an interface or inside one module, so that the owner can pivot later
without a rewrite. Ask the owner only for what the brief does not permit:
publishing, spending, contacting people, or a change of purpose.

Scale the ceremony to the budget:

| Budget | Plan | Skeleton by | Wind-down reserve | Document pack |
|---|---|---|---|---|
| under 1 hour | 5 minutes, top 3 backlog items | 40% | 10 minutes | README, DECISIONS, short handover |
| 1–6 hours | 10%, ranked backlog | 25% | 15%, at least 20 minutes | full pack, lighter guides |
| several runs | first run only; refresh each run | first run | 15% of each run | full pack, kept current |

## Phases

### 1. Orient and plan

Read the brief, its acceptance examples, any reference look or product, and
the repository's instructions. Write `PLAN.md`: the purpose in a sentence,
who the recipient is, the stack and why, and a ranked backlog. Each backlog
item says what the recipient gains. The backlog is a living list. Re-rank it
after every merge.

When resuming a multi-run build, read `PLAN.md`, `DECISIONS.md` and the
handover first. They are the build's memory, and they must be enough to
continue without the previous run's context.

### 2. Walking skeleton on main

Get the thinnest end-to-end version onto `main` early: it builds, runs from
the README's own commands, and passes its checks. Create the document pack
skeleton in the same merge. From here, `main` is always shippable.

### 3. The improvement loop

Repeat until only the wind-down reserve is left:

1. **Pick** the backlog item with the best value to the recipient for its
   cost. Mix features, polish, robustness and documentation. Polish counts as
   much as features.
2. **Branch.** Work on a feature branch or worktree. Commit work in progress
   there freely, never on `main`.
3. **Build and verify** (see "Verification" below), including the first-touch
   gate and fresh screenshots for anything a user sees.
4. **Review.** Every significant change gets a reviewer who did not write it:
   a delegated agent, or a fresh-context subagent. See
   [delegation](references/delegation.md).
5. **Merge** only when checks pass and review findings are fixed or recorded.
   Update the document pack in the same merge, so that docs never lag `main`.
6. **Re-rank** the backlog with what you learned.

**Stopping early.** Stop before the budget only when the best remaining item
is judged marginal or harmful: more risk, clutter or maintenance than value.
Record that judgement in the handover, with the items you considered and why
each one falls short. "The requirements pass" is not a reason to stop.

### 4. Wind-down

Start the wind-down when the reserve is reached, whatever is in flight. Leave
an unfinished branch committed and named in the handover. Do not rush it into
`main`. Then:

- run the full verification on `main` once more, including the first-touch gate;
- run an independent playtest or usage pass on the final build, so the last
  word comes from a fresh user, not the builder;
- finish the document pack, the scorecard and the retro;
- under a charter, close out through `charter-cycle`.

If the run is cut short without a wind-down, the rules above mean `main` still
builds, matches its docs, and the decisions log says what was happening.

## Verification

- **Automated checks:** unit, integration and end-to-end tests for behaviour
  the product promises. Tests check outcomes, not the wording of acceptance
  examples.
- **First-touch gate:** run every command the README and handover tell a
  person to type, exactly as written. Use a fresh clone when you can. For
  anything with a user interface, open each result in a real browser or
  window at phone and desktop sizes and look at the screenshots. Development
  and production modes must both work and look the same. A product whose
  quick-start command shows a broken page has failed, whatever its tests say.
- **Acceptance examples:** play each one through the real build. Report pass
  rates for anything non-deterministic.
- **Inspection surfaces:** every subsystem whose behaviour a user cannot see
  directly (a model, an AI opponent, an economy, a sync engine, a scheduler)
  gets a debug view that the owner can turn on themselves: which path produced
  an output, its inputs, timing, and anything that replaced or filtered it.
  The owner should not need the builder's test files to tell whether a feature
  works.
- **Polish review:** a fresh-context judge scores the product against the
  [polish rubric](references/polish-review.md), from screenshots and a short
  recording. Fix the low scores, then re-judge. Put the final scores on the
  handover.
- **Security pass:** a short threat model, then the scanners suited to the
  stack (code, dependencies, secrets, and a web baseline scan for anything
  served). Fix what is found or record why it was left. Do this before the
  wind-down, so its fixes go through the loop like any other change.

## Leading a team of agents

The lead agent owns `main`, the backlog, the decisions and every merge.
Delegate work that has a clear interface and a check that can judge it:
a plugin against an extension contract, a module behind an interface, a
review, a playtest, a security scan, a document pass. Keep scope, priorities
and taste with the lead. Delegated agents can be subagents, or agents from
another vendor run through their command-line interface. The
[delegation reference](references/delegation.md) covers briefs, isolation,
review and attribution.

Design for delegation. Extension points with a written contract, a template
and a conformance test turn each new feature into a self-contained task that
another agent can build and the lead can check.

## Publication and boundaries

Building a deployable artifact is in scope. Deploying it, publishing it,
releasing it or posting about it requires explicit authorization (for example
a charter's `publishes` field). Without one, stage the artifact, write the
deploy steps in the document pack, and report publication as outstanding.
Paid services and contacting people likewise need authorization.

## Handover

End every run with a handover the recipient can act on: what the product does
now, how to run it, what changed this run, the scorecard (requirements passing,
polish scores, security findings, time, tokens and spend, which agents did
what), the decisions worth revisiting, and the top of the backlog with reasons.
The [document pack](references/document-pack.md) lists the full set.
