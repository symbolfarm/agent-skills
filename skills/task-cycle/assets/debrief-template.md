# Debrief: [task-id] Title

**Completed:** YYYY-MM-DD
**Commit:** abc1234

<!-- Written for a future agent picking this up cold, NOT for the user
     (they get the report in the session chat). Do not restate what
     shipped — `git show` does that better and cannot drift. Record what
     git cannot recover: what didn't happen, and why things went the way
     they did. -->

## Design decisions

Any choice made during the work that deviated from the brief, wasn't
pre-specified, or involved a non-obvious trade-off — even small or
easily reversible ones. Record *why* it went that way, not just what
was chosen; the reasoning is the part that doesn't survive elsewhere.
Write "None — followed brief as written" if nothing applies.

## Descoped / deferred

What was left out, and — importantly — the condition under which it
should be picked back up. If nothing, write "Nothing descoped."

## Observations

Hidden constraints encountered, tricky edge cases, performance notes,
things that would trip up the next agent. Skip anything obvious from
reading the code.

## Follow-ups

Triage every follow-up into one of three buckets (see SKILL.md
"Triage candidate tasks"). Omit any bucket that's empty.

### Filed as tasks

- **[task-id]** Short title — one sentence on why it's needed

### Drive-by cleanup landed

- One line per drive-by: what changed and which commit landed it.

### Considered and dropped

- One line per candidate that on reflection wasn't worth filing,
  with the reason — saves future-you from re-raising it.
