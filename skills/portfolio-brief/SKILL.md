---
name: portfolio-brief
description: Report structured worker close-outs and independently checked scheduler health between portfolio reviews. Does not execute or authorize work.
metadata:
  version: "16"
---

# Portfolio brief

Read the portfolio's `WORKFLOW.md`, `WORKERS.json` and fresh `QUEUE.json`.
Historical goals/tasks are not backlog. Structured worker close-outs are the
primary briefing input; they point to canonical commits, checks, digests and
research records rather than copying them.

At the start of a scheduled brief, inspect the persisted cron record for the
previous completed invocation. Classify `last_status: ok` with positive delivery
evidence as `success`, `delivery_failed` as `failed`, and unverified, queued,
missing or ambiguous delivery as `unknown`; never infer success from generation
alone. Capture an offset-aware cutoff timestamp, then use the queue helper's
durable window command:

```
python3 <script> --queue <portfolio>/QUEUE.json brief-window \
  --previous-delivery <success|failed|unknown> --through <ISO timestamp> \
  --earliest <ISO timestamp>
```

The helper advances the prior pending cursor only after confirmed success, stages
the current cutoff, and returns entries across calendar files. Failed or unknown
delivery therefore replays unsent material; successful delivery advances exactly
once. Pass `--earliest` as the start of the window to use only while nothing has
ever been confirmed delivered — without it, a deployment whose first delivery keeps
failing replays its whole history each time. Use `reports --since` only for
diagnostics, not scheduled cursor management.

For every configured worker, check its independent `health` source. A close-out
and a scheduler execution establish different facts: distinguish a healthy no-op,
completed or resumable work, a failed run, a missed run, and a run whose reporting
step failed. For Hermes cron, inspect the persisted job/execution state. For a file
health source, read the configured host-produced record, its timestamp as well as
its status: a `completed` record older than the expected run window, or a `running`
record older than the worker's hard timeout, is evidence the worker did not
complete a run — report it as missed or crashed, never as healthy. An `incomplete`
record means the agent exited cleanly but left its claim held or wrote no close-out;
report it as a stalled run needing recovery. A host that
cannot reach the workspace at all cannot write its record, so absence together with
an expected run that left no trace is itself the finding. Absence of a close-out is
not evidence of an outage; absence of an expected execution is not an empty queue.
Never diagnose beyond the available evidence.

Render a concise, phone-readable report. Lead with a missed or failed run; otherwise
lead with the most meaningful change in understanding or capability. Group healthy
no-ops, but name any charter the helper reports as `awaiting_close`: it needs a
closing decision at the next review. For each substantive entry report its worker, charter/requirement, result,
direct evidence pointer and continuation or decision needed. Link a new digest
with enough context to explain why it matters. Do not redo a repository-wide
evidence tour merely to paraphrase a verified close-out; investigate a contradiction
before repeating it.

An intentionally empty fresh queue is a valid state. Do not derive work from themes,
generate replacement charters, inspect historical queues for candidates, re-rank,
execute work or mutate scheduler jobs. Themes inform interactive charter discussion
only. Recommendations are allowed when explicitly requested, but only the user may
authorize a charter or name its eligible workers.

Use the current conversation or an already authorized delivery channel. Preserve
existing delivery and `attach_to_session` settings so replies are ordinary follow-up
conversation. The recurring job should remain agent-backed for health reconciliation
and conversational attachment; it is not merely a script that prints a file.
