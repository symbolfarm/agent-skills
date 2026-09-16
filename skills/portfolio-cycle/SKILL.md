---
name: portfolio-cycle
description: Discuss research direction, review meaningful results, draft and authorize bounded charters, and order the fresh charter queue with the user.
license: MIT
metadata:
  version: "14"
---

# Portfolio cycle

Conversation supplies direction; repository evidence informs it. Read the
portfolio's `WORKFLOW.md` and fresh `QUEUE.json`, then only the research context
needed for the discussion. Old goals and tasks provide history, not commitments
to migrate. Do not turn a workflow discussion into an automatic full review.

## Understand and frame

Identify the question or outcome the user cares about, what is already known,
and what would make progress useful. Echo consequential ambiguities briefly.
Do not manufacture alternative readings or questions when intent is clear.

Themes preserve direction and motivation and sit above execution. Agents may draft
them from the user's expressed intent during this authorized planning conversation;
the user owns strategic choices. Themes do not generate work or assign workers.
A charter gives bounded execution authority, with requirements sized by meaning
rather than task count. Use `../charter-cycle/assets/charter-template.md` when
helpful.

Draft requirements with observable evidence of satisfaction, research context,
permitted repositories/actions, resource limits and meaningful stop conditions.
For research questions, permit credible negative answers and adaptive experiment
design. A performance target remains unmet when an experiment misses it.

The user authorizes a charter and names its eligible workers. Record actual
approval, including approval given in ordinary conversation; never ask for a
second ceremonial confirmation. Put the charter in the fresh queue only under
that authorization. Requirements are authored collaboratively; agents may not
relax them to claim completion. Worker profiles contribute factual capabilities,
wind-down limits, health sources and report sinks—not strategic priority.

## Review and steer

Lead with what changed in understanding or capability, supported by artifacts.
Distinguish observation, agent interpretation and the user's strategic choice.
Discuss the one or two consequences most worth attention, rather than reading
out the backlog. A useful review need not change the queue or graduate a policy.

Record agreed steering in the relevant charter/queue. Changing requirement order
can be a cheap recorded instruction. Preserve evidence when a requirement is
revised or dropped. Agents may propose next charters after findings or in review;
empty capacity alone is not a reason to generate work.

Use `QUEUE.json` for ordered charter references and requirement lifecycle; use
charter prose for intent and acceptance conditions. Read the schema beside
`../../scripts/charter_queue.py` in `references/fresh-queue.md` when filing work.
Do not copy requirement wording into the queue or import historical tasks in bulk.

## Execution and communication

`charter-cycle` executes, with tasks sized roughly to a context and generated only
as needed. `research-notebook` preserves current understanding. `digest` transfers
meaningful findings. `portfolio-brief` reports their consequences between reviews.
Keep these outputs proportional to the work; do not require every output per run.

Qualified research conclusions may be recorded without human ratification.
Authority to spend, publish, contact others or change strategic direction must
still come from the user and applicable local policy. The user may explicitly
authorize a process change here; agents do not expand their own authority.

Record agreed decisions briefly and commit portfolio changes separately from
implementation repositories. Historical rationale belongs in history, not in
the next worker's required reading. Scheduler wiring is installation-specific;
see `references/hermes-deployment.md` when updating it, and verify live state
separately from repository configuration.
