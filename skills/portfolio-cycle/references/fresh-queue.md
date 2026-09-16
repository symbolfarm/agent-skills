# Fresh queue

`QUEUE.json` lives in the private portfolio. Paths are relative to that directory.
Charters are ordered here; each charter's requirement array is its default work
order. Charter prose owns purpose, requirement wording, bounds and communication.
The queue owns authorization, routing and lifecycle. Use stable ids and a Markdown
heading `### R1 — title` for every requirement, including any dropped requirement.

Example (invented):

```json
{
  "version": 1,
  "charters": [{
    "id": "C-001",
    "path": "charters/C-001.md",
    "status": "draft",
    "authorized_by": null,
    "lane": "research",
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

Record the user's actual authorization in `authorized_by` and set `status: active`
only after approval. Never copy this example as live authorized work. `lane` may
be `research`, `product`, or `any`; workers can only select their lane or `any`.
`requires` lists capabilities the caller verifies; no capability is inferred
from a model name. Repository permission must also permit the intended actions.

Requirement states: ready, active (claim held), blocked (reason in progress),
deferred (user-held), done (evidence), dropped (user decision with reason).
Only completed dependencies unblock children; dropping a dependency requires
explicit review of the dependent requirement. Charter states: draft, active,
paused, closed. Closing a charter requires every requirement done or dropped.

The helper serializes queue mutations with `.charter-queue.lock` (gitignore it),
atomically writes the queue and acquires `.tasks/.lock` in each work repository.
Ensure repository locks are gitignored before unattended use. One active claim
serializes scheduled charter workers across lanes. The four-hour lock expiry is
diagnostic, never permission for automatic takeover. Review abandoned work before
`recover`; dirty files are preserved and still prevent a fresh claim.

Keep the portfolio as the control repository, not a requirement work repository:
claim commits and lifecycle updates occur there. For a direct maintenance session,
use ordinary interactive authorization and coordinate with any active worker.

`task` creates `.tasks/current/<id>.md` with parent and charter links and records
its path in the requirement. Historical `.tasks/LOG.jsonl` files are never scanned.
Requirement closeout needs primary evidence; the helper checks that it is present
and work repositories are clean, while the agent is responsible for judging its
meaning. JSON validation is not scientific verification.

Commands: `validate`, `next`, `claim`, `task`, `finish`, `check-exit`, `recover`.
Run `python3 <skills-repo>/scripts/charter_queue.py --help` for arguments.
