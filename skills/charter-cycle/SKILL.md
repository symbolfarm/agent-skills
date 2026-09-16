---
name: charter-cycle
description: Execute authorized charter requirements from a fresh queue, preserve research context across tasks, and close with evidence and a useful handover. Use for scheduled charter work or when asked to work a charter.
license: MIT
metadata:
  version: "3"
---

# Charter cycle

The user chooses direction, authorizes charters and assigns eligible workers.
Agents may draft themes and requirements in an authorized planning conversation,
but themes are non-executable and a draft grants no authority. Do not derive or
activate a charter merely because a theme has headroom or the queue is empty.
Explicit user steering updates the applicable instruction; record it without
demanding a second approval ritual. Do not weaken a success condition to declare
success.

## Orient and select

Read the portfolio's `WORKFLOW.md`, `QUEUE.json`, the selected charter, and the
relevant research overview. Historical queues are reference material only.
Read repository instructions before editing. Where a project registry exists,
verify active state and permission for the intended edits/commits; a charter does
not silently reopen an archived or human-only repository. The portfolio queue
orders charters; requirements follow their declared order and dependencies.
Explicit worker eligibility and profile capabilities determine
whether work can run, not its strategic rank. Never fall back to old tasks.

Use `../../scripts/charter_queue.py` relative to this skill. Scheduled workers
are defined by the portfolio's `WORKERS.json`; their profile supplies a stable
identity prefix, verified capabilities, wind-down budget, health source and
structured-report sink. Charters name their `eligible_workers` when the user
authorizes them. Themes provide direction but are never executable work and do
not route a charter automatically.

```
python3 <script> --queue <portfolio>/QUEUE.json next --worker <worker-id>
python3 <script> --queue <portfolio>/QUEUE.json claim --worker <worker-id> --holder <unique-run-id>
```

The holder must begin with the profile's `holder_prefix` followed by `-`. The
helper derives capabilities from the profile; callers must not claim capabilities
ad hoc. A null selection is a successful no-op. Missing/malformed configuration,
an unknown worker or an active requirement no eligible worker can run is an error,
not an empty queue. `next` is advisory; `claim` selects again under an atomic queue
lock and acquires repository locks before recording ownership. Concurrent scheduled
work is serialized for now. A Git commit alone is not a lock in a shared worktree.

The queue contains lifecycle/routing data; the charter owns requirement wording.
An entry is executable only with `status: active` and `authorized_by` recording
actual user authorization. Only the user can activate a draft or lift a deferral.
Commit a successful claim before implementation. Never claim with a reused run id.

## Interpret, then work

Briefly state the research question/outcome as understood, what would constitute
a useful answer, consequential assumptions, and the first step. Proceed under
existing authority; ask only when the unresolved interpretation would materially
change the work or cross a boundary. Record an unresolved question beside the
requirement in its progress or blocked reason so it survives the session.

Decompose as learning requires. A task is roughly one context and is useful when
work needs a handoff/restart; no task is necessary for work completed directly.
Do not manufacture a complete future task tree before investigating.

For a durable task, the helper creates a brief carrying the parent requirement
and records its path on the claimed requirement:

```
python3 <script> --queue <queue> task --token <claim-token> --repo <repo-path> --id EXP-1 --title 'Compare the baseline'
```

Fill its research context, intended check and continuation notes before handoff.
Tasks live in `.tasks/current/`; old `.tasks/LOG.jsonl` is not a selection source.
Revise or split tasks within the charter. Keep the requirement's outcome fixed
unless the user changes it. Repository lists locate authorized work; incidental
caller/test/doc edits inside them do not need another approval.

For research, record setup before running, preserve observations and negative
results, investigate credible alternatives within the budget, and update current
understanding with evidence, uncertainty and provenance. An agent's qualified
assessment need not wait for human ratification. Never present it as the user's
endorsement or independently corroborate a claim by repeating another report.

## Close or leave a continuation

Verify the requirement itself. Completing tasks or passing unrelated tests is
insufficient. Record a direct evidence reference and explain what it establishes.
Superseded documentation is deleted, or moved under an `archive/` path — never
left in place with a note on top. The path is what a later reader or a grep
result shows; a banner is invisible until the file is already open, and an agent
without memory of the decision will follow what it finds. No live document links
to an archived one, because links are how stale text keeps circulating. Do this
at close-out, for the documents the work touched, rather than as a separate
sweep. Dated records, digests and notebook notes are evidence rather than
instructions: those stay where they are and take a visible correction instead.

Use `digest` when the result materially changes what its reader understands or
can do, at a meaningful finding or charter closure; no automatic per-task digest.
A digest may recommend a next step while distinguishing evidence from advice.

Commit work before the queue transition. The helper releases only locks bearing
this claim's token:

```
python3 <script> --queue <queue> finish --token <claim-token> --state done --evidence 'repo commit/path: what this establishes'
python3 <script> --queue <queue> finish --token <claim-token> --state ready --note 'Result so far; exact next action and context'
python3 <script> --queue <queue> finish --token <claim-token> --state blocked --note 'Decision needed, why, and independent work remaining'
python3 <script> --queue <queue> check-exit --holder <unique-run-id>
```

After `check-exit` passes, every scheduled run writes one bounded close-out through
the helper, including a healthy no-op. The report is transport rather than primary
evidence: point to commits, checks, digests or notebook entries instead of copying
them. Use `completed` only with evidence, `advanced` only with an exact continuation,
and a unique holder so retries cannot duplicate an entry:

```
python3 <script> --queue <queue> report --worker <worker-id> \
  --holder <unique-run-id> --state completed --item <charter/requirement> \
  --summary 'What changed and why it matters' --evidence 'commit/path: check'
```

For a no-op omit `--item` and use `--state no-op`. A reporting failure does not
rewrite a verified queue transition, but it must be named in the final response.
The configured wind-down reserve exists to leave enough time for commit, `finish`,
`check-exit` and this report; do not begin new work inside it.

Use `ready` for resumable work and `blocked` only when no further authorized
progress on that requirement is possible. Commit the queue update and verify
clean worktrees. A task brief's completion note records its result; the queue's
evidence independently establishes requirement completion. Charter completion
is derived from all requirements being done or explicitly dropped by the user.

Budget scheduled runs by execution time or context-sized work, not by completed
requirements of arbitrary size. Preserve continuation before context/time runs
out. Release `ready` only with the work committed: uncommitted residue makes the
requirement unselectable on the next run, including by you resuming it. An active
claim holds the whole queue, so `next` reports an expired one as stalled with the
command that clears it. A stale claim requires inspection; `recover --item <id>
--reason ...` (or `--token`) releases it only after confirming the previous worker
is no longer running and preserving its work. An expired claim is never seized
automatically. Never clear another worker's dirty files to make work eligible.
