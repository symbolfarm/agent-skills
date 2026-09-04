#!/usr/bin/env python3
"""Detect unfinished lifecycle claims in portfolio goal and task records."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

GOAL_START = re.compile(r"^- \*\*(G-\d+)\*\*")
CLAIM = re.compile(r"\*Claimed:\*\s*([^,\n]+),\s*(\S+)")
PROGRESS = re.compile(r"\*Progress:\*")


@dataclass(frozen=True)
class Goal:
    identifier: str
    section: str
    text: str
    claimant: str | None
    claimed_at: dt.datetime | None
    has_progress: bool

    @property
    def has_open_claim(self) -> bool:
        return self.section == "Queue" and self.claimant is not None and not self.has_progress


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp has no timezone: {value}")
    return parsed


def parse_goals(path: Path) -> dict[str, Goal]:
    goals: dict[str, Goal] = {}
    section = ""
    identifier: str | None = None
    lines: list[str] = []

    def finish() -> None:
        nonlocal identifier, lines
        if identifier is None:
            return
        text = "\n".join(lines)
        match = CLAIM.search(text)
        claimant = match.group(1).strip() if match else None
        claimed_at = parse_time(match.group(2)) if match else None
        goals[identifier] = Goal(identifier, section, text, claimant, claimed_at, bool(PROGRESS.search(text)))
        identifier, lines = None, []

    for line in path.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            finish()
            section = heading.group(1).strip()
            continue
        start = GOAL_START.match(line)
        if start:
            finish()
            identifier = start.group(1)
            lines = [line]
        elif identifier is not None:
            lines.append(line)
    finish()
    return goals


def goal_exit(path: Path, identifiers: list[str]) -> int:
    goals = parse_goals(path)
    failures: list[str] = []
    for identifier in identifiers:
        goal = goals.get(identifier)
        if goal is None:
            failures.append(f"{identifier}: missing from goal ledger")
        elif goal.has_open_claim:
            assert goal.claimed_at is not None
            failures.append(
                f"{identifier}: open claim by {goal.claimant} since {goal.claimed_at.isoformat()} "
                "has no completion, block, or Progress record"
            )
    if failures:
        print("RUN EXIT REFUSED — unresolved lifecycle claim(s):", file=sys.stderr)
        print("\n".join(f"- {failure}" for failure in failures), file=sys.stderr)
        return 1
    print("Run-exit lifecycle check passed: " + ", ".join(identifiers))
    return 0


def task_exit(path: Path, identifiers: list[str]) -> int:
    records = {
        record["id"]: record
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for record in [json.loads(line)]
    }
    failures = []
    for identifier in identifiers:
        record = records.get(identifier)
        if record is None:
            failures.append(f"{identifier}: missing from task ledger")
        elif record.get("status") == "in_progress":
            failures.append(f"{identifier}: task remains in_progress")
    if failures:
        print("RUN EXIT REFUSED — unresolved lifecycle claim(s):", file=sys.stderr)
        print("\n".join(f"- {failure}" for failure in failures), file=sys.stderr)
        return 1
    print("Run-exit lifecycle check passed: " + ", ".join(identifiers))
    return 0


def stale_claims(path: Path, older_than_minutes: float, now: dt.datetime) -> int:
    cutoff = now - dt.timedelta(minutes=older_than_minutes)
    stale = [
        goal for goal in parse_goals(path).values()
        if goal.has_open_claim and goal.claimed_at is not None and goal.claimed_at < cutoff
    ]
    if not stale:
        print("No unmatched claims older than the lane wind-down")
        return 0
    print("STALE UNMATCHED CLAIMS:")
    for goal in stale:
        claimed_at = goal.claimed_at
        assert claimed_at is not None
        age = now - claimed_at.astimezone(now.tzinfo)
        minutes = int(age.total_seconds() // 60)
        print(f"- {goal.identifier}: claimed by {goal.claimant} at {claimed_at.isoformat()} ({minutes} minutes old)")
    return 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)

    goal = commands.add_parser("goal-exit", help="refuse exit with an unresolved goal claim")
    goal.add_argument("goals", type=Path)
    goal.add_argument("identifiers", nargs="+")

    task = commands.add_parser("task-exit", help="refuse exit with an in-progress task")
    task.add_argument("log", type=Path)
    task.add_argument("identifiers", nargs="+")

    stale = commands.add_parser("stale-claims", help="report old unmatched portfolio claims")
    stale.add_argument("goals", type=Path)
    stale.add_argument("--older-than-minutes", type=float, required=True)
    stale.add_argument("--now", type=parse_time, default=dt.datetime.now(dt.timezone.utc))
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "goal-exit":
        return goal_exit(args.goals, args.identifiers)
    if args.command == "task-exit":
        return task_exit(args.log, args.identifiers)
    return stale_claims(args.goals, args.older_than_minutes, args.now)


if __name__ == "__main__":
    raise SystemExit(main())
