#!/usr/bin/env python3
"""Validate a portfolio-cycle repository using only the Python standard library."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

STATUSES = {"active", "paused", "candidate", "incubating", "completed"}
ATTENTION = {"primary", "secondary", "maintenance", "watch", "unranked"}
CYCLES = {"task", "research", "none"}
AUTOMATION_MODES = {"cron_allowed", "manual_only", "paused"}
PLAN_STATUSES = {"draft", "frozen", "cancelled"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def load_json(path: Path, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing required file: {path}")
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}")
    except OSError as exc:
        errors.append(f"cannot read {path}: {exc}")
    return None


def require_dict(value: Any, where: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{where} must be an object")
        return None
    return value


def require_nonempty_string(value: Any, where: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where} must be a non-empty string")
        return None
    return value.strip()


def validate_registry(data: Any, root: Path) -> tuple[list[str], list[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    warnings: list[str] = []
    projects_by_id: dict[str, dict[str, Any]] = {}
    obj = require_dict(data, "PROJECTS.json", errors)
    if obj is None:
        return errors, warnings, projects_by_id

    if obj.get("schema_version") != 1:
        errors.append("PROJECTS.json schema_version must be 1")

    workspace_root = obj.get("workspace_root")
    if not isinstance(workspace_root, str) or not Path(workspace_root).is_absolute():
        errors.append("PROJECTS.json workspace_root must be an absolute path")

    timezone = require_nonempty_string(obj.get("timezone"), "PROJECTS.json timezone", errors)
    if timezone and "/" not in timezone:
        warnings.append("PROJECTS.json timezone should normally be an IANA name such as Australia/Adelaide")

    planning = require_dict(obj.get("planning"), "PROJECTS.json planning", errors)
    if planning is not None:
        max_packets = planning.get("max_packets_per_day")
        if not isinstance(max_packets, int) or isinstance(max_packets, bool) or max_packets < 1:
            errors.append("planning.max_packets_per_day must be a positive integer")
        max_parallel = planning.get("max_parallel_projects")
        if not isinstance(max_parallel, int) or isinstance(max_parallel, bool) or max_parallel < 1:
            errors.append("planning.max_parallel_projects must be a positive integer")
        if planning.get("push") is not False:
            errors.append("planning.push must be false for the safe MVP policy")
        window = require_dict(planning.get("work_window"), "planning.work_window", errors)
        if window:
            for key in ("start", "end"):
                value = window.get(key)
                if not isinstance(value, str) or not TIME_RE.match(value):
                    errors.append(f"planning.work_window.{key} must be HH:MM")

    projects = obj.get("projects")
    if not isinstance(projects, list):
        errors.append("PROJECTS.json projects must be an array")
        return errors, warnings, projects_by_id

    active_ranks: list[int] = []
    primary_ids: list[str] = []
    paths: list[str] = []

    for index, project_value in enumerate(projects):
        where = f"projects[{index}]"
        project = require_dict(project_value, where, errors)
        if project is None:
            continue

        project_id = require_nonempty_string(project.get("id"), f"{where}.id", errors)
        if project_id:
            if not ID_RE.match(project_id):
                errors.append(f"{where}.id must use lowercase letters, digits, and hyphens")
            if project_id in projects_by_id:
                errors.append(f"duplicate project id: {project_id}")
            else:
                projects_by_id[project_id] = project

        require_nonempty_string(project.get("name"), f"{where}.name", errors)
        path_value = require_nonempty_string(project.get("path"), f"{where}.path", errors)
        if path_value:
            path = Path(path_value)
            if not path.is_absolute():
                errors.append(f"{where}.path must be absolute")
            paths.append(path_value)
            if not path.exists():
                warnings.append(f"{project_id or where}: path does not exist: {path}")

        status = project.get("status")
        if status not in STATUSES:
            errors.append(f"{where}.status must be one of {sorted(STATUSES)}")
        attention = project.get("attention")
        if attention not in ATTENTION:
            errors.append(f"{where}.attention must be one of {sorted(ATTENTION)}")
        cycle = project.get("cycle")
        if cycle not in CYCLES:
            errors.append(f"{where}.cycle must be one of {sorted(CYCLES)}")

        rank = project.get("rank")
        if rank is not None and (not isinstance(rank, int) or isinstance(rank, bool) or rank < 1):
            errors.append(f"{where}.rank must be null or a positive integer")
        if status == "active":
            if rank is None:
                errors.append(f"{where}: active projects require a rank")
            else:
                active_ranks.append(rank)
            if attention == "unranked":
                errors.append(f"{where}: active projects cannot have unranked attention")
            if attention == "primary" and project_id:
                primary_ids.append(project_id)
        elif rank is not None:
            warnings.append(f"{project_id or where}: non-active project has rank {rank}")

        skills = project.get("skills")
        if not isinstance(skills, list) or not skills or not all(isinstance(s, str) and s for s in skills):
            errors.append(f"{where}.skills must be a non-empty array of skill names")

        automation = require_dict(project.get("automation"), f"{where}.automation", errors)
        if automation:
            if automation.get("mode") not in AUTOMATION_MODES:
                errors.append(f"{where}.automation.mode must be one of {sorted(AUTOMATION_MODES)}")
            if not isinstance(automation.get("commit"), bool):
                errors.append(f"{where}.automation.commit must be boolean")
            if automation.get("push") is not False:
                errors.append(f"{where}.automation.push must be false for the safe MVP policy")
            if status != "active" and automation.get("mode") == "cron_allowed":
                errors.append(f"{where}: only active projects may be cron_allowed")

        daily_limit = project.get("daily_task_limit")
        if not isinstance(daily_limit, int) or isinstance(daily_limit, bool) or daily_limit < 0:
            errors.append(f"{where}.daily_task_limit must be a non-negative integer")

    duplicate_ranks = [rank for rank, count in Counter(active_ranks).items() if count > 1]
    if duplicate_ranks:
        errors.append(f"active project ranks must be unique; duplicates: {sorted(duplicate_ranks)}")
    duplicate_paths = [path for path, count in Counter(paths).items() if count > 1]
    if duplicate_paths:
        errors.append(f"project paths must be unique; duplicates: {duplicate_paths}")
    if len(primary_ids) > 1:
        errors.append(f"at most one active project may be primary; found: {primary_ids}")
    if projects and not primary_ids:
        warnings.append("no active primary project is selected")

    return errors, warnings, projects_by_id


def validate_plan(
    data: Any,
    path: Path,
    registry: dict[str, Any],
    projects_by_id: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    obj = require_dict(data, str(path), errors)
    if obj is None:
        return errors, warnings

    if obj.get("schema_version") != 1:
        errors.append(f"{path}: schema_version must be 1")
    date = obj.get("date")
    if not isinstance(date, str) or not DATE_RE.match(date):
        errors.append(f"{path}: date must be YYYY-MM-DD")
    elif path.stem != date:
        errors.append(f"{path}: filename must match date field")
    status = obj.get("status")
    if status not in PLAN_STATUSES:
        errors.append(f"{path}: status must be one of {sorted(PLAN_STATUSES)}")

    packets = obj.get("packets")
    if not isinstance(packets, list):
        errors.append(f"{path}: packets must be an array")
        return errors, warnings

    planning = registry.get("planning", {}) if isinstance(registry, dict) else {}
    max_packets = planning.get("max_packets_per_day")
    if isinstance(max_packets, int) and len(packets) > max_packets:
        errors.append(f"{path}: {len(packets)} packets exceeds portfolio limit {max_packets}")

    packet_ids: list[str] = []
    project_tasks: list[tuple[str, str]] = []
    project_counts: Counter[str] = Counter()

    for index, packet_value in enumerate(packets):
        where = f"{path}: packets[{index}]"
        packet = require_dict(packet_value, where, errors)
        if packet is None:
            continue
        packet_id = require_nonempty_string(packet.get("id"), f"{where}.id", errors)
        if packet_id:
            packet_ids.append(packet_id)
        project_id = require_nonempty_string(packet.get("project"), f"{where}.project", errors)
        task_id = require_nonempty_string(packet.get("task_id"), f"{where}.task_id", errors)
        project = projects_by_id.get(project_id or "")
        if project_id and project is None:
            errors.append(f"{where}: unknown project {project_id}")
        elif project is not None:
            assert project_id is not None
            project_counts[project_id] += 1
            if packet.get("path") != project.get("path"):
                errors.append(f"{where}.path does not match PROJECTS.json for {project_id}")
            if packet.get("skills") != project.get("skills"):
                warnings.append(f"{where}.skills differs from registry order for {project_id}")
            if status == "frozen":
                automation = project.get("automation", {})
                if project.get("status") != "active" or automation.get("mode") != "cron_allowed":
                    errors.append(f"{where}: frozen packet targets project not allowed for cron")
                if automation.get("commit") is not True:
                    errors.append(f"{where}: frozen packet requires project automation.commit=true")
            if task_id:
                project_tasks.append((project_id, task_id))

        skills = packet.get("skills")
        if not isinstance(skills, list) or not skills or not all(isinstance(s, str) and s for s in skills):
            errors.append(f"{where}.skills must be a non-empty array")
        execution = require_dict(packet.get("execution"), f"{where}.execution", errors)
        if execution:
            if execution.get("push") is not False:
                errors.append(f"{where}.execution.push must be false")
            if execution.get("commit") is not True:
                errors.append(f"{where}.execution.commit must be true")
            if execution.get("stop_on_ambiguity") is not True:
                errors.append(f"{where}.execution.stop_on_ambiguity must be true")
        require_nonempty_string(packet.get("stop_condition"), f"{where}.stop_condition", errors)

    duplicates = [value for value, count in Counter(packet_ids).items() if count > 1]
    if duplicates:
        errors.append(f"{path}: duplicate packet ids: {duplicates}")
    duplicate_tasks = [value for value, count in Counter(project_tasks).items() if count > 1]
    if duplicate_tasks:
        errors.append(f"{path}: duplicate project/task packets: {duplicate_tasks}")
    for project_id, count in project_counts.items():
        limit = projects_by_id[project_id].get("daily_task_limit")
        if isinstance(limit, int) and count > limit:
            errors.append(f"{path}: {project_id} has {count} packets, exceeding daily_task_limit {limit}")

    return errors, warnings


def validate(root: Path) -> tuple[list[str], list[str]]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    registry_path = root / "PROJECTS.json"
    registry = load_json(registry_path, errors)
    if registry is None:
        return errors, warnings

    reg_errors, reg_warnings, projects_by_id = validate_registry(registry, root)
    errors.extend(reg_errors)
    warnings.extend(reg_warnings)

    for required in ("PORTFOLIO.md", "DECISIONS.md"):
        if not (root / required).is_file():
            errors.append(f"missing required file: {root / required}")
    for required_dir in ("plans", "reviews", "scripts"):
        if not (root / required_dir).is_dir():
            errors.append(f"missing required directory: {root / required_dir}")

    plans_dir = root / "plans"
    if plans_dir.is_dir():
        for plan_path in sorted(plans_dir.glob("*.json")):
            plan = load_json(plan_path, errors)
            if plan is None:
                continue
            plan_errors, plan_warnings = validate_plan(plan, plan_path, registry, projects_by_id)
            errors.extend(plan_errors)
            warnings.extend(plan_warnings)

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path, help="portfolio repository root")
    args = parser.parse_args(argv)
    errors, warnings = validate(args.root)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: portfolio is valid ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
