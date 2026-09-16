---
name: work-cycle
description: Carry out a direct user request or a task under an authorized charter. Use for implementation and handoff; historical repository queues are not automatically executable.
license: MIT
metadata:
  version: "10"
---

# Work cycle

For scheduled work or an authorized charter, use `charter-cycle`. Direct user
requests remain sufficient authority within their stated scope; do not require
a charter for ordinary interactive work.

Read the repository instructions and relevant research context. Preserve other
people's edits. When sharing a repository, use its atomic lock protocol before
editing; a commit does not provide mutual exclusion in a shared worktree.

State consequential assumptions briefly, then proceed. Ask only for a material
ambiguity, exceeded budget or action outside authorization. Necessary tests,
caller updates and documentation belong to implementing the agreed outcome.

Create a durable task when a handoff or restart needs one. Under a charter use
its task helper, which records the parent requirement automatically. A task
should fit roughly one context; split or revise it when learning requires it.
Old task ledgers are historical context, never a source of newly authorized work.

Verify the requested behavior, commit at useful boundaries when authorized, and
leave evidence plus an exact continuation if unfinished. Do not require separate
filing, implementation and housekeeping commits for every small change.

For research, preserve findings, negative results and uncertainty in the project's
current research record. Use `research-notebook` for its correction discipline.
An evidence-backed agent assessment does not require human ratification; the
user retains strategic direction and external commitments.

Superseded documentation is deleted, or moved under an `archive/` path — never
left in place with a note on top. The path is what a later reader or a grep
result shows; a banner is invisible until the file is already open, and an agent
without memory of the decision will follow what it finds. No live document links
to an archived one, because links are how stale text keeps circulating. Do this
at close-out, for the documents the work touched, rather than as a separate
sweep. Dated records, digests and notebook notes are evidence rather than
instructions: those stay where they are and take a visible correction instead.

Use `digest` when the result changes what the reader needs to understand or use.
Routine changes need a concise handover, not a separate report. Scheduled workers
do not push; any existing host publication boundary still applies.

The scripts retained in this directory support historical records. They do not
validate the fresh charter queue; `charter-cycle` names its own lifecycle check.
