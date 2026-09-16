# Repository availability and the lock protocol

Inherited unchanged from `work-cycle`. These rules predate charters, are not
charter-specific, and were not rewritten for this entry point — where the wording
differs from `work-cycle`'s, `work-cycle`'s is correct and this file is the defect.

## Availability

A repository is available when its worktree is clean and no other agent holds a live
`.tasks/.lock`. Check the item's repository before claiming it. `repo_availability.py`
reports one repository's state, and its `first_available` applies the rule to a queue
in order. It lives in the **skills repository root**, not in any skill's own
`scripts/`, so resolve it two levels above this skill's directory:

```bash
python3 <charter-cycle-skill>/../../scripts/repo_availability.py <repo> [<repo> ...] \
    --holder <agent>
```

A worktree is clean only when `git status --porcelain` is empty. Unavailability is per
repository and skips only that repository's items.

**An unavailable repository costs its own items, never the run.** Skip every item
belonging to it — without claiming, moving, or blocking those items — continue down
the queue, and take the first item whose repository is available. A run that stops
because one repository was dirty has converted one stalled item into a stalled day.

## Do not clear the obstruction to make an item runnable

Uncommitted work is its author's: never `stash`, `clean`, `reset`, or commit it, and
never guess at what an untracked file was for. Replacing an *expired* lock is the
single exception.

## File the anomaly, then keep working

Record each unavailable repository once per run as an item in the same queue
substrate, carrying an `*Anomaly:* <repo> — <what was found>` line: the porcelain
paths, or the lock's holder and expiry. Say what would clear it, and mark it
`assignee: <user>` when the residue is theirs to rule on — uncommitted work an agent
must not guess at usually is.

The `*Anomaly:*` line is what lets a report distinguish an obstruction the lane routed
around from work someone chose to queue; without it a skipped repository reads as a
healthy backlog.

When the unavailable repository is the only one, leaving nowhere to file, report it in
the close-out and end the run as a no-op.

## The lock

After the claim, acquire `.tasks/.lock` atomically per the portfolio's `LOCKING.md`,
normally with `O_CREAT | O_EXCL`. The lock records holder, item, acquired time, and
expiry. Default TTL is two hours, adjusted to the work.

- **Live lock held by another agent:** do not wait or edit. Release the claim, file
  the anomaly, and take the next item whose repository is available — the lock blocks
  that repository, not the run.
- **Expired lock:** record that it is stale, replace it atomically, and continue.
- **Release** the lock after the final project commit and on every exit path.

Order is always item claim, then repository lock, then edit.
