---
name: charter-cycle
description: Execute authorized charter requirements from a fresh queue, preserve research context across tasks, and close with evidence and a useful handover. Use for scheduled charter work or when asked to work a charter.
license: MIT
metadata:
  version: "2"
---

# Charter cycle

The user chooses direction and authorizes charters. Agents may draft themes and
requirements from the conversation, but a draft grants no authority. Explicit
user steering updates the applicable instruction; record it without demanding a
second approval ritual. Do not weaken a success condition to declare success.

## Orient and select

Read the portfolio's `WORKFLOW.md`, `QUEUE.json`, the selected charter, and the
relevant research overview. Historical queues are reference material only.
Read repository instructions before editing. Where a project registry exists,
verify active state and permission for the intended edits/commits; a charter does
not silently reopen an archived or human-only repository. The portfolio queue orders charters;
requirements follow their declared order and dependencies. Lane and capability
filters determine eligibility, not strategic rank. Never fall back to old tasks.

Use `../../scripts/charter_queue.py` relative to this skill:

```
python3 <script> --queue <portfolio>/QUEUE.json next --lane research --capability general
python3 <script> --queue <portfolio>/QUEUE.json claim --lane research --capability general --holder <unique-run-id>
```

Repeat `--capability` for verified capabilities. Omit `--lane` only when the caller
allows all lanes. A null selection is a successful no-op. Missing/malformed
configuration is an error, not an empty queue. `next` is advisory; `claim` selects
again under an atomic queue lock and acquires repository locks before recording
ownership. Concurrent scheduled work is serialized for now. A Git commit alone
is not a lock in a shared worktree.

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
