#!/usr/bin/env python3
"""Emit a portfolio-cycle source snapshot for one task-cycle task."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def snapshot(project_root: Path, task_id: str, task_file: Path) -> dict[str, str]:
    root = project_root.resolve()
    if task_file.is_absolute():
        raise ValueError("task_file must be relative to the project root")
    task_path = (root / task_file).resolve()
    if not task_path.is_relative_to(root):
        raise ValueError("task_file must stay beneath the project root")
    if not task_path.is_file():
        raise ValueError(f"task file not found: {task_file}")

    log_path = root / ".tasks" / "LOG.jsonl"
    if not log_path.is_file():
        raise ValueError(f"task log not found: {log_path}")

    matching_lines: list[bytes] = []
    for number, raw_line in enumerate(log_path.read_bytes().splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"invalid JSON on {log_path}:{number}: {exc}") from exc
        if row.get("id") == task_id:
            matching_lines.append(raw_line)

    if len(matching_lines) != 1:
        raise ValueError(f"expected exactly one {task_id!r} log entry; found {len(matching_lines)}")

    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ValueError(f"cannot resolve project Git HEAD: {completed.stderr.strip()}")
    git_head = completed.stdout.strip()
    if not git_head:
        raise ValueError("project Git HEAD is empty")

    return {
        "task_file": task_file.as_posix(),
        "task_sha256": sha256(task_path.read_bytes()),
        "log_entry_sha256": sha256(matching_lines[0]),
        "git_head": git_head,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("task_id")
    parser.add_argument("task_file", type=Path, help="project-relative task file path")
    args = parser.parse_args(argv)
    try:
        result = snapshot(args.project_root, args.task_id, args.task_file)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
