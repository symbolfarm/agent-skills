# Availability and locking

Fresh charter work uses `scripts/charter_queue.py` from the skills repository.
It checks each required repository for uncommitted work and any existing lock,
then acquires `.tasks/.lock` by exclusive creation under the queue mutation lock.
A stale timestamp does not authorize takeover. Inspect the previous worker and
its changes before recovery. Never clear another author’s work to make an item run.

The old claim-commit-before-lock protocol is superseded: a Git commit alone does
not exclude another process in the same worktree. Preserve separate commits for
work and portfolio lifecycle, with the control repository clean before claiming.
