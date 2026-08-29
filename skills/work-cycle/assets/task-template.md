# [task-id] Title

**Priority:** high / medium / low
**Blocked by:** task-xxx, task-yyy (or "nothing")
**Depends-on (external):** sibling-repo PROJ-N (omit line if none — see SKILL.md "Multi-project workspaces")
**Touches:** `path/or/glob`, `path/or/glob` (or `unknown`)

<!-- Best-guess set of files/dirs this work will modify, used for
     conflict detection and parallel scheduling. Use `unknown` if you
     genuinely can't predict. See SKILL.md "Parallel-safe scheduling". -->

## Context

What led to this task? Why does it matter? What decisions have already
been made that affect this work? Write enough that an agent starting
cold can understand the situation without reading the full git history.

## Goal

One or two sentences. What does "done" look like?

## Acceptance criteria

- [ ] Criterion one
- [ ] Criterion two
- [ ] `cargo check` / `pnpm tsc --noEmit` pass clean
- [ ] Relevant tests pass

## Relevant files

List the files most likely to need reading or editing. Saves the agent
from a broad codebase scan.

- `src-tauri/src/...`
- `src/...`

## Decisions already made

Anything that was debated and settled — captures the "why" so it
doesn't get re-litigated.

- Decision one and rationale
- Decision two and rationale

## Out of scope

What this task explicitly does NOT cover (to prevent scope creep).
