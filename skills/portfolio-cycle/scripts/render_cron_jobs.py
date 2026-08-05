#!/usr/bin/env python3
"""Render a frozen schema-v2 portfolio plan into Hermes cronjob payloads."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_validator(root: Path):
    path = root / "scripts" / "validate_portfolio.py"
    spec = importlib.util.spec_from_file_location("validate_portfolio", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load validator from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def slot_prompt(plan_path: Path, slot: int, project_id: str) -> str:
    return f"""Execute portfolio slot {slot:02d} for project {project_id}.

Authoritative frozen plan: {plan_path}

The job workdir is the assigned project repository. Its AGENTS.md and related
project instructions are authoritative. Follow the attached task-cycle skill.
Read TASKS.md and .tasks/LOG.jsonl, then select the highest-priority pending,
unblocked task that is concrete and safe for unattended execution.

Preflight: require a clean worktree, no task already in_progress, an unchanged
frozen slot assignment, and no unresolved user decision. If any check fails or
there is no eligible task, make no edits and report a no-op. Do not invent,
broaden, split, or reprioritise work.

Complete at most one task. Follow task-cycle through implementation, tests,
debrief, log housekeeping, and local commits. Never push, merge, rebase, or
modify the portfolio repository. Report the slot, task, result, commits,
validation, and any user decision or review required.
"""


def render(root: Path, plan_path: Path) -> dict[str, Any]:
    root = root.resolve()
    plan_path = plan_path.resolve()
    registry_path = root / "PROJECTS.json"
    registry = load_json(registry_path)
    plan = load_json(plan_path)
    validator = load_validator(root)
    reg_errors, _warnings, projects = validator.validate_registry(registry, root)
    plan_errors, _warnings = validator.validate_plan(plan, plan_path, registry, projects)
    errors = reg_errors + plan_errors
    if errors:
        raise ValueError("invalid portfolio input:\n- " + "\n- ".join(errors))
    if plan.get("schema_version") != 2 or plan.get("status") != "frozen":
        raise ValueError("cron rendering requires a frozen schema_version 2 plan")

    schedule = plan["schedule"]
    defaults = plan["execution_defaults"]
    start = datetime.fromisoformat(schedule["start_at"])
    interval = timedelta(hours=schedule["interval_hours"])
    jobs: list[dict[str, Any]] = []
    for allocation in sorted(plan["slots"], key=lambda value: value["slot"]):
        slot = allocation["slot"]
        project_id = allocation["project"]
        project = projects[project_id]
        workdir = Path(project["path"])
        for required in ("AGENTS.md", "TASKS.md", ".tasks/LOG.jsonl"):
            if not (workdir / required).is_file():
                raise ValueError(f"{project_id}: missing required repository file {required}")
        run_at = start + interval * (slot - 1)
        payload = {
            "action": "create",
            "name": f"portfolio-{plan['date']}-slot-{slot:02d}-{project_id}",
            "schedule": run_at.isoformat(),
            "repeat": 1,
            "prompt": slot_prompt(plan_path, slot, project_id),
            "deliver": defaults["delivery"],
            "skills": ["task-cycle"],
            "enabled_toolsets": ["terminal", "file", "web"],
            "workdir": str(workdir),
            "attach_to_session": False,
        }
        jobs.append({
            "slot": slot,
            "project": project_id,
            "run_at": run_at.isoformat(),
            "cronjob_payload": payload,
        })

    return {
        "schema_version": 1,
        "source_plan": str(plan_path),
        "registry_revision": plan["registry_revision"],
        "job_count": len(jobs),
        "jobs": jobs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="frozen schema-v2 plan")
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = render(args.root, args.plan)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
