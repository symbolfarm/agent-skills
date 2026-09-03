# Strategic review and project archaeology

Load this reference during `portfolio-cycle` when a mature project may be
optimising details without advancing its purpose, or an old repository retains a
useful idea without an endorsed direction.

## Strategic-progress audit

Technical health is evidence, not strategic progress. Establish:

- the intended outcome and present value proposition;
- which recent work materially advanced that outcome;
- which work mainly added polish, validation, bookkeeping, or marginal content;
- whether related repositories still reinforce one another at their intended
  boundary;
- the smallest decision or outcome that would materially advance the project;
- what evidence would justify stopping rather than adding another goal.

A read-only audit may produce findings and bounded unfiled proposals. It may not
silently file, prioritise, or execute them. Strategy is settled interactively.

## Product archaeology before revival

Do not begin an old-project revival with dependency updates. Separate:

1. the enduring product idea and intended user experience;
2. reusable code, content, data models, tests, and design artifacts;
3. obsolete provider bindings, deployment choices, and architectural assumptions;
4. independent products or layers hidden inside the old application;
5. the smallest experiment that could validate each surviving proposition;
6. an explicit archive decision when no proposition still warrants attention.

Review product identity before repository topology. Split or modernise only after
the boundaries are understood well enough to avoid preserving obsolete structure
or generalising prematurely.

## Map the result onto the existing states

Do not create an `incubating` state merely because a project is being discussed.
Use the portfolio's existing axes:

- `active` with non-empty `agent_may`: may receive agreed goals and agent work;
- `active` with empty `agent_may`: alive but human-only while direction is scoped;
- `parked`: preserved without current attention; revival requires a priority
  decision;
- `archived`: retained as a record, with a deliberate restart required;
- `resource`: source material rather than an independent work target.

A clean repository with passing tests can still be strategically parked or
archived. Conversely, a rough repository can be active when a concrete outcome
is worth pursuing.

## Review-first sequence

1. Inspect bounded repository evidence.
2. Discuss value proposition, boundaries, and the stop/revival decision.
3. Record the agreed direction in the private portfolio or project design note.
4. File outcome goals only after their done-whens are stable.
5. Let `work-cycle` create implementation tasks when a handoff is useful.
6. Reconcile the next review against the strategic outcome, not commit volume.

If nobody can state what done would look like in one sentence, remain in scoping
mode. A repository's existence and available agent capacity are not reasons to
revive it.
