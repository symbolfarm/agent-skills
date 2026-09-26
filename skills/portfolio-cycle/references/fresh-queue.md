# Fresh queue

`QUEUE.json` lives in the private portfolio. Paths are relative to that directory.
Charters are ordered here; each charter's requirement array is its default work
order. Charter prose owns purpose, requirement wording, bounds and communication.
The queue owns authorization, worker eligibility and lifecycle. Use stable ids and
a Markdown heading `### R1 — title` for every requirement, including a dropped one.

Example (invented):

```json
{
  "version": 2,
  "charters": [{
    "id": "C-001",
    "path": "charters/C-001.md",
    "status": "draft",
    "authorized_by": null,
    "eligible_workers": ["general-morning"],
    "requirements": [{
      "id": "R1",
      "state": "ready",
      "repos": ["../example-research"],
      "requires": ["general"],
      "depends_on": []
    }]
  }]
}
```

Record the user's actual authorization in `authorized_by`, record the worker ids
they authorized in `eligible_workers`, and set `status: active` only after approval.
Never copy this example as live authorized work. Every worker id must exist in
`WORKERS.json`; every active requirement must be runnable by at least one named
worker. `requires` lists factual capabilities from worker profiles. Themes provide
direction but never create a charter, assign a worker or become executable work.
Repository permission must also permit the intended actions.

Requirement states: ready, active (claim held), blocked (reason in progress),
deferred (user-held), done (evidence), dropped (user decision with reason). Only
completed dependencies unblock children; dropping a dependency requires explicit
review of the dependent requirement. Charter states: draft, active, paused, closed.
Closing a charter requires every requirement done or dropped.

The helper serializes queue/report mutations with `.charter-queue.lock`, atomically
writes and commits the queue (`QUEUE.json` only), and acquires `.tasks/.lock` in
each work repository. Ensure repository locks are gitignored before unattended use.
Workers run concurrently with one claim each; a claim blocks only the repositories
it locked.

A charter's queue entry may carry `gpu_hours`, the GPU-hour budget the user sets
at authorization. It is the only thing that lets a worker start a detached job
(`job-start`), and the helper refuses a job that would exceed what remains.
Record the same number in the charter's prose budget. A worker profile's
`max_job_hours` is a scheduler fact — the longest job its host can keep running —
not a research budget. The four-hour lock expiry is diagnostic, never permission
for automatic takeover. Review abandoned work before `recover`; dirty files are
preserved and still prevent a fresh claim.

Keep the portfolio as the control repository, not a requirement work repository:
claim commits and lifecycle updates occur there. For direct maintenance, use
ordinary interactive authorization and coordinate with any active worker. To
complete or advance a requirement in session with the user, claim it as the
installation's `interactive` worker with `claim --item`.

`task` creates `.tasks/current/<id>.md` with parent and charter links and records
its path in the requirement. Historical `.tasks/LOG.jsonl` files are never scanned.
Requirement closeout needs primary evidence; the helper checks that it is present
and work repositories are clean, while the agent judges its meaning. JSON validation
is not scientific verification.

After `check-exit`, scheduled workers use `report`; the brief reads `reports --since`
and checks each worker's health source independently. See the charter-cycle
`worker-profiles-and-closeouts.md` reference for the anonymized deployment shape.

Commands: `validate`, `next`, `claim`, `task`, `finish`, `check-exit`, `recover`,
`report`, `reports`, `brief-window`. Run
`python3 <skills-repo>/scripts/charter_queue.py --help`.
