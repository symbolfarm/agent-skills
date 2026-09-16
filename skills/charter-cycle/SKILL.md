---
name: charter-cycle
description: >-
  Execute one unmet requirement from a ratified charter: select it, record how it
  will be discharged, work it under the charter's own decision levels and halt
  conditions, and close it with the digest the charter names. Use when asked to
  work a charter, take the next requirement, or continue in-flight charter work.
  Supersedes work-cycle for chartered work; work-cycle still runs everything else.
license: MIT
metadata:
  author: Symbol Farm
  version: "1"
  category: productivity
  tags: charters, requirements, execution, digests, charter-cycle
---

# Charter cycle

Work starts from a **charter** — a ratified, bounded grant of authority — not from a
queue position. One run discharges one requirement.

**A charter an agent drafted but the user has not ratified grants nothing.** Check
for `status: active` and a `ratified:` line before reading anything else. A draft is
readable; it is not workable, and an agent may never ratify its own.

## 1. Select one unmet requirement

**Charters are ranked; requirements inside one are not.** The user ranks charters —
each inherits its theme's position in the portfolio queue. Within a charter, take the
**first unmet requirement in table order**, honouring any dependency the charter
declares between requirements.

Skip a requirement when it is already discharged, a halt condition covering it is
live, another agent holds a live claim, or its repository is unavailable. Skipping is
not re-ranking: never reorder a charter's table to reach work. If nothing is workable,
name the charter and the reason and end the run — an empty charter is not a licence to
fall through to unchartered work.

**A requirement the user explicitly deferred is not selectable**, whatever the
charter's headroom, and the deferral does not expire because a day passed. Only the
user lifts it.

**An unavailable repository costs its own items, never the run.** Skip every item
belonging to it — without claiming, moving, or blocking those items — and continue.
A run that stops because one repository was dirty has converted one stalled item into
a stalled day. Availability, the anomaly record, and the rule against clearing
someone's uncommitted work are in
[`references/availability-and-locking.md`](references/availability-and-locking.md).

## 2. Claim, and declare the discharge shape

Record on the charter and commit **before any work**:

```
R3 — claimed by <agent>, <ISO-8601>, discharged as: one context, direct
R3 — claimed by <agent>, <ISO-8601>, discharged as: decomposed into 3 tasks
```

**The shape is declared at claim time, not discovered at close.** It is a prediction,
and a wrong one is a finding worth recording — a charter that mis-predicts
decomposition is evidence about the unit itself, which is why the claim commits
separately from the work.

Then acquire the repository lock. **Order is always claim, then lock, then edit.**

## 3. Work it under the charter's own rules

**Inside a charter's bounds its decision table is the operative one.** Precedence,
highest first: the floor, never varied by anything → the charter's table → the
portfolio's global defaults for any class the charter does not name.

| Level | Behaviour |
|---|---|
| `auto` | Decide and proceed; do not log it. |
| `report` | Decide and proceed; record the choice and the reasoning. |
| `ask` | Stop. Do not decide. Record what is needed. |

An unknown class is `unclassified` at report level. **Do not mint a class** — that
happens in a review, not on the execution path.

**Halt conditions are not obstacles to route around.** When one fires, stop, record
which one and what tripped it, and end the run. A halt is the charter working.

**Scope is the charter's, not the requirement's.** If discharging a requirement needs
something the charter placed out of scope, that is a halt condition rather than a
scope expansion.

When the declared shape is `decomposed`, file every task in the owning repository
before implementing any of it, then run them under `work-cycle`. A requirement that
fits one context is worked directly and never becomes a task.

## 4. Close with the digest the charter names

A requirement is discharged when its stated condition is true **and** its digest
exists.

**Read the `Digest` column.** Where it names a reader, the digest is owed to that
reader and written at *their* altitude — not the altitude the work was done at. Where
it is empty, no digest is owed and the close-out is the commit and the record.

**Resolving the digest's home** when the charter or requirement does not name one:

- a digest whose subject is **the charter** lands beside the charter;
- a digest whose subject is a **project artifact** lands in that project.

A calling project's page convention governs **format**, not location. Produce the
digest with the `digest` skill.

Then mark it discharged, commit, release the lock. When every requirement is
discharged or struck, say so and leave ratifying what comes next to the user.

### Run exit gate

**An assertion, not a remembered checklist item.** Before returning, run the shared
lifecycle guard over every item touched. It is not copied into this skill — there is
one guard, and it lives with the superseded entry point:

```bash
python3 <charter-cycle-skill>/../work-cycle/scripts/lifecycle_guard.py goal-exit \
  <portfolio>/GOALS.md G-002
python3 <charter-cycle-skill>/../work-cycle/scripts/lifecycle_guard.py task-exit \
  <repository>/.tasks/LOG.jsonl EX-4
```

A non-zero exit **refuses to end the run**: finish the close-out and rerun it. The
guard never releases or rewrites a claim.

## Boundaries

- Never ratify a charter, amend a requirement, or lift a deferral.
- Never create a theme or re-rank charters. `themes/` holds the direction a charter
  serves — read it for intent, never edit it here.
- Never delete a struck requirement: it stays visible with its reason, because tasks
  may cite it.
- Findings land **provisional**. What the research record says we believe is not an
  agent's to settle.
- **Falling back to `work-cycle` is a finding, not a failure.** Record what you reached
  for and why it was not here; see
  [`references/selection-and-fallback.md`](references/selection-and-fallback.md).

## Checklist

- [ ] Charter is active and ratified; no draft was worked.
- [ ] First unmet requirement in table order, dependencies honoured, nothing reordered.
- [ ] Discharge shape declared at claim time, committed before the work.
- [ ] Claim, then lock, then edit — lock released on every exit path.
- [ ] Decisions taken against the charter's table, with the floor above it.
- [ ] A fired halt condition ended the run and was recorded.
- [ ] The digest the charter names exists, at its reader's altitude, in the right home.
- [ ] Lifecycle guard run and clean; any `work-cycle` fallback recorded.
