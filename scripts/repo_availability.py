#!/usr/bin/env python3
"""Report whether repositories are available for `work-cycle` to edit.

A repository is unavailable when its worktree is dirty (someone else's
uncommitted work) or when `.tasks/.lock` is held by another agent and has not
expired. Availability is per repository, so one blocked repository should cost
one item rather than the whole run: `first_available` picks the first queue
item whose repository can actually be worked.

Usage:
    repo_availability.py <repo> [<repo> ...] [--holder NAME] [--now ISO8601]
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


LOCK_RELPATH = Path(".tasks") / ".lock"


@dataclass(frozen=True)
class Availability:
    """Whether one repository may be edited, and why not when it may not."""

    repo: str
    available: bool
    reason: str | None
    detail: str

    def as_dict(self) -> dict:
        return asdict(self)


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(timezone.utc)


def worktree_residue(repo: Path) -> list[str]:
    """Porcelain lines for a repository, empty when the worktree is clean."""
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git status failed")
    return [line for line in result.stdout.splitlines() if line.strip()]


def read_lock(repo: Path) -> dict | None:
    """Parse `.tasks/.lock`, or None when no lock file exists.

    A lock that exists but does not parse returns an empty mapping: the
    repository is held by something, and guessing is the failure mode this
    check exists to avoid.
    """
    lock = repo / LOCK_RELPATH
    if not lock.is_file():
        return None
    try:
        payload = json.loads(lock.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _expiry(payload: dict) -> datetime | None:
    raw = payload.get("expires_at")
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def check(repo: Path, holder: str | None = None, now: datetime | None = None) -> Availability:
    """Classify one repository as available, dirty, locked, or missing."""
    name = repo.name
    if not (repo / ".git").exists():
        return Availability(name, False, "missing", f"{repo} is not a git repository")

    try:
        residue = worktree_residue(repo)
    except RuntimeError as error:
        return Availability(name, False, "missing", str(error))
    if residue:
        shown = ", ".join(residue[:3])
        more = f" (+{len(residue) - 3} more)" if len(residue) > 3 else ""
        return Availability(name, False, "dirty", f"{len(residue)} uncommitted path(s): {shown}{more}")

    payload = read_lock(repo)
    if payload is None:
        return Availability(name, True, None, "clean worktree, no lock")
    if not payload:
        return Availability(name, False, "locked", "lock file present but unreadable")

    lock_holder = payload.get("holder")
    if holder is not None and lock_holder == holder:
        return Availability(name, True, None, f"lock already held by {holder}")

    expires = _expiry(payload)
    if expires is None:
        return Availability(name, False, "locked", f"lock held by {lock_holder} with no readable expiry")
    if expires <= _now(now):
        return Availability(name, True, None, f"stale lock from {lock_holder} expired {expires.isoformat()}")
    return Availability(name, False, "locked", f"held by {lock_holder} until {expires.isoformat()}")


def first_available(
    items: list[tuple[str, Path]],
    holder: str | None = None,
    now: datetime | None = None,
) -> tuple[tuple[str, Path] | None, list[tuple[str, Availability]]]:
    """Return the first workable item, plus the availability of each item skipped.

    `items` is in queue order — position is priority — as (item id, repository)
    pairs. The skipped list is what a run reports and files as anomalies; it is
    returned even when nothing is workable.
    """
    skipped: list[tuple[str, Availability]] = []
    cache: dict[Path, Availability] = {}
    for item_id, repo in items:
        state = cache.get(repo)
        if state is None:
            state = check(repo, holder=holder, now=now)
            cache[repo] = state
        if state.available:
            return (item_id, repo), skipped
        skipped.append((item_id, state))
    return None, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repos", nargs="+", type=Path)
    parser.add_argument("--holder", default=None, help="agent name; its own lock does not block it")
    parser.add_argument("--now", default=None, help="ISO-8601 instant to evaluate lock expiry against")
    args = parser.parse_args(argv)

    now = datetime.fromisoformat(args.now) if args.now else None
    states = [check(repo, holder=args.holder, now=now) for repo in args.repos]
    print(json.dumps([state.as_dict() for state in states], indent=2))
    return 0 if all(state.available for state in states) else 1


if __name__ == "__main__":
    sys.exit(main())
