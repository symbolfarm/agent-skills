#!/usr/bin/env python3
"""Fresh charter queue, worker profiles, claims, close-outs and report windows.

Only QUEUE.json and WORKERS.json provide execution state; historical goal/task
ledgers are never discovered. Mutations use flock plus atomic replacement.
Repository O_EXCL locks interoperate with existing workers. No automatic
stale-lock takeover is performed: an expired claim is reported with the command
that clears it, never seized.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid
from zoneinfo import ZoneInfo

from repo_availability import worktree_residue

STATES = {"ready", "active", "blocked", "deferred", "done", "dropped"}
SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")
RUN_ID = re.compile(r"[A-Za-z0-9_.:-]+")
REPORT_STATES = {"no-op", "advanced", "completed", "blocked", "failed"}
REPORT_RECORD = re.compile(r"<!-- worker-closeout: (\{.*\}) -->")

# Two charter forms are in use: the template writes `### R1 — ...`, while the
# human-machine-teaming charters write a requirements table. Both declare the
# same thing, so both are read rather than forcing one to be rewritten.
REQUIREMENT_HEADING = re.compile(r"^#{2,4} (R[1-9][0-9]*)\b", re.M)
REQUIREMENT_ROW = re.compile(r"^\|\s*\**\s*(R[1-9][0-9]*)\s*\**\s*\|", re.M)


def declared_requirements(contract):
    """The set of requirement ids the charter prose declares, in either form.

    Ids recur legitimately — a discharged charter keys both its requirements
    table and its evidence table by id — so this counts nothing. The check it
    serves is only that the charter and the queue agree on which requirements
    exist; a repeated row is a prose error, not a reason to freeze the queue.
    """
    return set(REQUIREMENT_HEADING.findall(contract) + REQUIREMENT_ROW.findall(contract))


def safe_relative(root, value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    relative = Path(value)
    resolved = (root / relative).resolve()
    if relative.is_absolute() or resolved != root.resolve() and root.resolve() not in resolved.parents:
        raise ValueError(f"{label} must stay inside the portfolio")
    return resolved


def read_workers(path):
    data = json.loads(path.read_text())
    if (not isinstance(data, dict) or data.get("version") != 1
            or not isinstance(data.get("workers"), list)):
        raise ValueError("WORKERS.json: expected version 1 and workers list")
    if set(data) != {"version", "timezone", "workers"}:
        raise ValueError("WORKERS.json: unknown top-level field")
    try:
        ZoneInfo(data["timezone"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("WORKERS.json: invalid IANA timezone") from error
    workers = {}
    prefixes = set()
    for worker in data["workers"]:
        if not isinstance(worker, dict):
            raise ValueError("WORKERS.json: every worker must be an object")
        if set(worker) != {"id", "holder_prefix", "capabilities", "wind_down",
                           "report_sink", "health"}:
            raise ValueError("WORKERS.json: unknown or missing worker field")
        worker_id = worker.get("id")
        if not isinstance(worker_id, str) or not SAFE_ID.fullmatch(worker_id) or worker_id in workers:
            raise ValueError("WORKERS.json: duplicate or invalid worker id")
        prefix = worker.get("holder_prefix")
        if (not isinstance(prefix, str) or not SAFE_ID.fullmatch(prefix)
                or prefix in prefixes):
            raise ValueError(f"WORKERS.json: {worker_id} has duplicate or invalid holder_prefix")
        prefixes.add(prefix)
        capabilities = worker.get("capabilities")
        if (not isinstance(capabilities, list) or len(capabilities) != len(set(capabilities))
                or not all(isinstance(c, str) and SAFE_ID.fullmatch(c) for c in capabilities)):
            raise ValueError(f"WORKERS.json: {worker_id} has invalid capabilities")
        wind_down = worker.get("wind_down", {})
        if not isinstance(wind_down, dict):
            raise ValueError(f"WORKERS.json: {worker_id} has invalid wind_down")
        if set(wind_down) != {"minutes", "reserve_minutes"}:
            raise ValueError(f"WORKERS.json: {worker_id} has invalid wind_down fields")
        minutes = wind_down.get("minutes")
        reserve = wind_down.get("reserve_minutes")
        if (type(minutes) is not int or type(reserve) is not int
                or minutes <= 0 or reserve <= 0 or reserve >= minutes):
            raise ValueError(f"WORKERS.json: {worker_id} has invalid wind_down")
        safe_relative(path.parent, worker.get("report_sink", ""),
                      f"WORKERS.json: {worker_id} report_sink")
        health = worker.get("health", {})
        if not isinstance(health, dict):
            raise ValueError(f"WORKERS.json: {worker_id} has invalid health")
        if health.get("kind") == "hermes-cron":
            if (set(health) != {"kind", "job_id"}
                    or not isinstance(health.get("job_id"), str)
                    or not health["job_id"].strip()):
                raise ValueError(f"WORKERS.json: {worker_id} health needs job_id")
        elif health.get("kind") == "file":
            if set(health) != {"kind", "path"}:
                raise ValueError(f"WORKERS.json: {worker_id} health needs only path")
            safe_relative(path.parent, health.get("path", ""),
                          f"WORKERS.json: {worker_id} health path")
        else:
            raise ValueError(f"WORKERS.json: {worker_id} has invalid health kind")
        workers[worker_id] = worker
    if not workers:
        raise ValueError("WORKERS.json: at least one worker is required")
    return data, workers


def read_queue(path, workers):
    data = json.loads(path.read_text())
    if data.get("version") != 2 or not isinstance(data.get("charters"), list):
        raise ValueError("expected version 2 and charters list")
    ids = set()
    for charter in data["charters"]:
        cid = charter["id"]
        if cid in ids or not SAFE_ID.fullmatch(cid):
            raise ValueError("duplicate or invalid charter id")
        ids.add(cid)
        if charter["status"] not in {"draft", "active", "paused", "closed"}:
            raise ValueError(f"{cid}: invalid charter status")
        if charter["status"] == "active" and not charter.get("authorized_by"):
            raise ValueError(f"{cid}: active charter has no authorization record")
        source = safe_relative(path.parent, charter["path"], f"{cid}: charter path")
        contract = source.read_text()
        eligible = charter.get("eligible_workers", [])
        if not isinstance(eligible, list) or len(set(eligible)) != len(eligible):
            raise ValueError(f"{cid}: eligible_workers must be a unique list")
        if charter["status"] != "draft" and not eligible:
            raise ValueError(f"{cid}: authorized charter needs eligible_workers")
        unknown = sorted(set(eligible) - set(workers))
        if unknown:
            raise ValueError(f"{cid}: unknown eligible worker: {', '.join(unknown)}")
        requirements = charter["requirements"]
        rids = [r["id"] for r in requirements]
        if len(set(rids)) != len(rids) or not rids:
            raise ValueError(f"{cid}: duplicate or empty requirements")
        if declared_requirements(contract) != set(rids):
            raise ValueError(f"{cid}: requirement ids differ from those the charter declares")
        for req in requirements:
            if req["state"] not in STATES or not req.get("repos"):
                raise ValueError(f"{cid}/{req['id']}: invalid state or missing repositories")
            requires = req.get("requires", [])
            if (not isinstance(requires, list) or len(set(requires)) != len(requires)
                    or not all(isinstance(c, str) and SAFE_ID.fullmatch(c) for c in requires)):
                raise ValueError(f"{cid}/{req['id']}: invalid required capabilities")
            if (charter["status"] == "active" and req["state"] not in {"done", "dropped"}
                    and not any(
                    set(requires).issubset(set(workers[worker]["capabilities"]))
                    for worker in eligible)):
                raise ValueError(f"{cid}/{req['id']}: no eligible worker has required capabilities")
            if path.parent.resolve() in repo_paths(path, req):
                raise ValueError(f"{cid}: portfolio is the control repository, not a work repository")
            for dep in req.get("depends_on", []):
                if dep not in rids or dep == req["id"]:
                    raise ValueError(f"{cid}: invalid dependency {dep}")
            if req["state"] == "done" and not req.get("evidence"):
                raise ValueError(f"{cid}/{req['id']}: done requires evidence")
            if req["state"] == "active" and not req.get("claim"):
                raise ValueError(f"{cid}/{req['id']}: active requires a claim")
            if req["state"] != "active" and req.get("claim"):
                raise ValueError(f"{cid}/{req['id']}: unexpected claim")
            transitions = req.get("transitions", [])
            if not isinstance(transitions, list):
                raise ValueError(f"{cid}/{req['id']}: transitions must be a list")
            for transition in transitions:
                if (not isinstance(transition, dict)
                        or set(transition) != {"holder", "state", "at"}
                        or not RUN_ID.fullmatch(transition.get("holder", ""))
                        or transition.get("state") not in {"ready", "blocked", "done"}):
                    raise ValueError(f"{cid}/{req['id']}: invalid transition record")
                timestamp = datetime.fromisoformat(transition["at"])
                if timestamp.utcoffset() is None:
                    raise ValueError(f"{cid}/{req['id']}: transition timestamp needs offset")
        if charter["status"] == "closed" and any(r["state"] not in {"done", "dropped"} for r in requirements):
            raise ValueError(f"{cid}: closed charter has unmet requirements")
        visited, visiting = set(), set()
        def visit(rid):
            if rid in visiting:
                raise ValueError(f"{cid}: cyclic dependencies")
            if rid in visited:
                return
            visiting.add(rid)
            for dep in next(r for r in requirements if r['id'] == rid).get('depends_on', []):
                visit(dep)
            visiting.remove(rid)
            visited.add(rid)
        for rid in rids:
            visit(rid)
    return data


def rows(data):
    for charter in data["charters"]:
        for req in charter["requirements"]:
            yield charter, req


def save(path, data):
    # mkstemp is 0600. Replacing the queue with that would lock a second worker
    # running as a different user out of the shared queue after the first claim.
    mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
    fd, name = tempfile.mkstemp(prefix=".queue-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def transaction(path, workers):
    with (path.parent / ".charter-queue.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = read_queue(path, workers)
        yield data


def repo_paths(path, req):
    return sorted({(path.parent / r).resolve() for r in req["repos"]})


def choose(path, data, worker):
    skipped = []
    worker_id = worker["id"]
    capabilities = set(worker["capabilities"])
    # Serial execution avoids simultaneous commits to shared portfolio state.
    # An active claim anywhere holds the whole queue, so a worker that died
    # mid-requirement stalls both lanes. Report that as a stall naming the
    # command that clears it: seizing a claim whose worker may still be running
    # is the one failure this serialisation exists to prevent.
    now = datetime.now(timezone.utc)
    active = []
    for charter, req in rows(data):
        if req['state'] != 'active':
            continue
        claim = req.get('claim', {})
        expires = claim.get('expires_at')
        item = f"{charter['id']}/{req['id']}"
        active.append({"item": item, "holder": claim.get('holder'),
                       "expires_at": expires,
                       "expired": bool(expires and datetime.fromisoformat(expires) < now),
                       "clear_with": f"recover --item {item} --reason '<why the previous worker is gone>'"})
    if active:
        return None, [{"reason": "active claim requires completion or recovery",
                       "stalled": any(entry["expired"] for entry in active),
                       "items": active}]
    for charter, req in rows(data):
        key = f"{charter['id']}/{req['id']}"
        if charter['status'] != 'active' or req['state'] != 'ready':
            continue
        if worker_id not in charter['eligible_workers']:
            continue
        if not set(req.get('requires', [])).issubset(capabilities):
            skipped.append({"item": key, "reason": "missing capability"})
            continue
        states = {r['id']: r['state'] for r in charter['requirements']}
        if any(states[d] != 'done' for d in req.get('depends_on', [])):
            skipped.append({"item": key, "reason": "dependency not satisfied"})
            continue
        reason = None
        for repo in repo_paths(path, req):
            if not (repo / '.git').exists():
                reason = f"missing repository: {repo}"
                break
            if (repo / '.tasks/.lock').exists():
                reason = f"repository lock present: {repo}"
                break
            if worktree_residue(repo):
                reason = f"dirty repository: {repo}"
                break
        if reason:
            skipped.append({"item": key, "reason": reason})
            continue
        return (charter, req), skipped
    return None, skipped


def describe(path, pair):
    if pair is None:
        return None
    charter, req = pair
    return {"item": f"{charter['id']}/{req['id']}",
            "charter": str((path.parent / charter['path']).resolve()),
            "requirement": req}


def resolve_token(data, args):
    item = getattr(args, 'item', None)
    if not item:
        return args.token
    for charter, req in rows(data):
        if f"{charter['id']}/{req['id']}" == item and req.get('claim'):
            return req['claim']['token']
    raise ValueError(f'no active claim on {item}')


def owned(data, token):
    matches = [(c, r) for c, r in rows(data) if r.get('claim', {}).get('token') == token]
    if len(matches) != 1:
        raise ValueError('claim token not found or ambiguous')
    return matches[0]


def release(paths, token):
    for repo in paths:
        lock = repo / '.tasks/.lock'
        if lock.exists():
            payload = json.loads(lock.read_text())
            if payload.get('token') != token:
                raise ValueError(f'lock ownership changed: {repo}')
    for repo in paths:
        lock = repo / '.tasks/.lock'
        if lock.exists():
            lock.unlink()


def check_exit(path, data, holder):
    if any(r.get('claim', {}).get('holder') == holder for _, r in rows(data)):
        raise ValueError('unclosed requirement claim remains for this run')
    for repo in {repo for _, req in rows(data) for repo in repo_paths(path, req)}:
        lock = repo / '.tasks/.lock'
        if lock.exists() and json.loads(lock.read_text()).get('holder') == holder:
            raise ValueError(f'unreleased repository lock: {repo}')


def atomic_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
    fd, name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def one_line(value, label):
    if value is None:
        return None
    value = value.strip()
    if not value or '\n' in value or '\r' in value:
        raise ValueError(f'{label} must be one non-empty line')
    return value


def aware_timestamp(value, label):
    timestamp = datetime.fromisoformat(value)
    if timestamp.utcoffset() is None:
        raise ValueError(f'{label} must include a timezone offset')
    return timestamp


def report_entries(sinks, since=None, through=None):
    entries = []
    for sink in sorted(set(sinks)):
        if not sink.exists():
            continue
        for path in sorted(sink.glob('*.md')):
            for line in path.read_text().splitlines():
                match = REPORT_RECORD.fullmatch(line)
                if not match:
                    continue
                entry = json.loads(match.group(1))
                timestamp = aware_timestamp(entry['timestamp'], 'report timestamp')
                if (since is None or timestamp > since) and (through is None or timestamp <= through):
                    entries.append(entry)
    ordered = sorted(entries, key=lambda entry: (entry['timestamp'], entry['run_id']))
    unique = {}
    for entry in ordered:
        prior = unique.get(entry['run_id'])
        if prior is not None and prior != entry:
            raise ValueError(f"conflicting duplicate report run id: {entry['run_id']}")
        unique[entry['run_id']] = entry
    return list(unique.values())


def brief_window(path, workers, args):
    through = aware_timestamp(args.through, '--through')
    cursor_path = path.parent / '.briefing/brief-cursor.json'
    cursor = {'version': 1, 'delivered_through': None, 'pending_through': None}
    if cursor_path.exists():
        cursor = json.loads(cursor_path.read_text())
        if (not isinstance(cursor, dict) or cursor.get('version') != 1
                or set(cursor) != {'version', 'delivered_through', 'pending_through'}):
            raise ValueError('invalid briefing cursor')
    delivered = cursor['delivered_through']
    pending = cursor['pending_through']
    if args.previous_delivery == 'success' and pending:
        delivered = pending
    since = aware_timestamp(delivered, 'briefing cursor') if delivered else None
    if since is not None and through < since:
        raise ValueError('--through precedes the delivered briefing cursor')
    sinks = [safe_relative(path.parent, worker['report_sink'], 'report_sink')
             for worker in workers.values()]
    entries = report_entries(sinks, since, through)
    atomic_text(cursor_path, json.dumps({
        'version': 1,
        'delivered_through': delivered,
        'pending_through': through.isoformat(),
    }, indent=2) + '\n')
    return {
        'since': delivered,
        'through': through.isoformat(),
        'previous_delivery': args.previous_delivery,
        'reports': entries,
    }


def write_report(path, workers_data, workers, data, args):
    worker = workers.get(args.worker)
    if worker is None:
        raise ValueError(f'unknown worker: {args.worker}')
    prefix = worker['holder_prefix'] + '-'
    if not RUN_ID.fullmatch(args.holder) or not args.holder.startswith(prefix):
        raise ValueError(f'holder must begin {prefix}')
    check_exit(path, data, args.holder)
    if (path.parent / '.git').exists() and worktree_residue(path.parent):
        raise ValueError('commit the control-repository transition before reporting')
    if args.state not in REPORT_STATES:
        raise ValueError('invalid report state')
    item = one_line(args.item, 'item')
    known_items = {f"{charter['id']}/{req['id']}": req for charter, req in rows(data)}
    if item and item not in known_items:
        raise ValueError(f'unknown report item: {item}')
    if args.state in {'advanced', 'completed', 'blocked'} and not item:
        raise ValueError(f'{args.state} report requires an item')
    if args.state == 'no-op' and item:
        raise ValueError('no-op report must not name an item')
    summary = one_line(args.summary, 'summary')
    continuation = one_line(args.continuation, 'continuation')
    evidence = [one_line(value, 'evidence') for value in args.evidence]
    if args.state == 'advanced' and not continuation:
        raise ValueError('advanced report requires a continuation')
    if args.state == 'completed' and not evidence:
        raise ValueError('completed report requires evidence')
    expected_states = {'advanced': 'ready', 'completed': 'done', 'blocked': 'blocked'}
    if item and args.state in expected_states:
        matching = [transition for transition in known_items[item].get('transitions', [])
                    if transition['holder'] == args.holder
                    and transition['state'] == expected_states[args.state]]
        if not matching:
            raise ValueError(
                f"{args.state} report requires a matching durable transition for {item}")
    timezone_name = workers_data['timezone']
    now = datetime.now(ZoneInfo(timezone_name))
    sink = safe_relative(path.parent, worker['report_sink'], 'report_sink')
    existing = report_entries([sink])
    if any(entry['run_id'] == args.holder for entry in existing):
        raise ValueError(f'duplicate report run id: {args.holder}')
    payload = {
        'version': 1,
        'timestamp': now.isoformat(),
        'worker': args.worker,
        'run_id': args.holder,
        'state': args.state,
        'item': item,
        'summary': summary,
        'evidence': evidence,
        'continuation': continuation,
    }
    report = sink / f'{now.date().isoformat()}.md'
    content = report.read_text() if report.exists() else (
        f'# Worker close-outs — {now.date().isoformat()}\n\n')
    lines = [
        f"<!-- worker-closeout: {json.dumps(payload, separators=(',', ':'))} -->",
        f"## {now.strftime('%H:%M')} — {args.worker}",
        '',
        f"- Run: `{args.holder}`",
        f"- Status: `{args.state}`",
    ]
    if item:
        lines.append(f"- Work: `{item}`")
    lines.append(f"- Result: {summary}")
    for value in evidence:
        lines.append(f"- Evidence: {value}")
    if continuation:
        lines.append(f"- Continuation: {continuation}")
    atomic_text(report, content.rstrip() + '\n\n' + '\n'.join(lines) + '\n')
    return {'report': str(report), 'entry': payload}


def run(args):
    path = args.queue.resolve()
    workers_data, workers = read_workers(path.parent / 'WORKERS.json')
    if args.command in {'next', 'validate', 'check-exit', 'reports'}:
        data = read_queue(path, workers)
        if args.command == 'validate':
            return {'valid': True, 'charters': len(data['charters']), 'workers': len(workers)}
        if args.command == 'check-exit':
            check_exit(path, data, args.holder)
            return {'clean': True}
        if args.command == 'reports':
            since = aware_timestamp(args.since, '--since') if args.since else None
            sinks = [safe_relative(path.parent, worker['report_sink'], 'report_sink')
                     for worker in workers.values()]
            return {'reports': report_entries(sinks, since)}
        worker = workers.get(args.worker)
        if worker is None:
            raise ValueError(f'unknown worker: {args.worker}')
        selected, skipped = choose(path, data, worker)
        return {'selected': describe(path, selected), 'skipped': skipped}
    with transaction(path, workers) as data:
        if args.command == 'brief-window':
            return brief_window(path, workers, args)
        if args.command == 'report':
            return write_report(path, workers_data, workers, data, args)
        if args.command == 'claim':
            worker = workers.get(args.worker)
            if worker is None:
                raise ValueError(f'unknown worker: {args.worker}')
            prefix = worker['holder_prefix'] + '-'
            if not RUN_ID.fullmatch(args.holder) or not args.holder.startswith(prefix):
                raise ValueError(f'holder must begin {prefix}')
            sink = safe_relative(path.parent, worker['report_sink'], 'report_sink')
            if any(entry['run_id'] == args.holder for entry in report_entries([sink])):
                raise ValueError(f'run id already has a close-out: {args.holder}')
            if (path.parent / '.git').exists() and worktree_residue(path.parent):
                raise ValueError('commit or preserve control-repository changes before claiming')
            selected, skipped = choose(path, data, worker)
            if selected is None:
                return {'selected': None, 'skipped': skipped}
            charter, req = selected
            token = uuid.uuid4().hex
            now = datetime.now(timezone.utc)
            claim = {'holder': args.holder, 'token': token, 'acquired_at': now.isoformat(),
                     'expires_at': (now + timedelta(hours=4)).isoformat(),
                     'item': f"{charter['id']}/{req['id']}"}
            acquired = []
            try:
                for repo in repo_paths(path, req):
                    lock = repo / '.tasks/.lock'
                    lock.parent.mkdir(exist_ok=True)
                    with lock.open('x') as f:
                        acquired.append(repo)
                        json.dump(claim, f)
                req['claim'] = claim
                req['state'] = 'active'
                save(path, data)
            except Exception:
                release(acquired, token)
                raise
            return {'selected': describe(path, selected), 'skipped': skipped}
        token = resolve_token(data, args)
        charter, req = owned(data, token)
        repos = repo_paths(path, req)
        if args.command == 'task':
            repo = args.repo.resolve()
            if repo not in repos or not re.fullmatch(r'[A-Za-z0-9_-]+', args.id):
                raise ValueError('task must have a safe id and belong to a claimed repository')
            dest = repo / '.tasks/current' / f'{args.id}.md'
            dest.parent.mkdir(parents=True, exist_ok=True)
            parent = f"{charter['id']}/{req['id']}"
            body = (f"# {args.id} — {args.title}\n\nParent: {parent}\n"
                    f"Charter: {os.path.relpath(path.parent / charter['path'], dest.parent)}\n\n"
                    "## Context\n\nRelevant theory, evidence and decisions for a fresh agent.\n\n"
                    "## Work and check\n\nBounded action and observable acceptance evidence.\n\n"
                    "## Continuation / result\n\nExact next step, or result and evidence when complete.\n")
            with dest.open('x') as f:
                f.write(body)
            req.setdefault('tasks', []).append(os.path.relpath(dest, path.parent))
            save(path, data)
            return {'task': str(dest), 'parent': parent}
        recovering = args.command == 'recover'
        state = 'ready' if recovering else args.state
        note = args.reason if recovering else args.note
        evidence = [] if recovering else args.evidence
        if state == 'done' and (not evidence or not all(e.strip() for e in evidence)):
            raise ValueError('completion requires evidence of the requirement itself')
        if state != 'done' and (not note or not note.strip()):
            raise ValueError('continuation, block or recovery requires a note')
        if state in {'done', 'ready'}:
            # `choose` skips a dirty repository, so residue left behind here makes
            # this requirement unselectable on the next run — including by the
            # worker that meant to resume it.
            for repo in repos:
                if worktree_residue(repo):
                    raise ValueError(
                        f'commit the work before recording {state}: {repo} '
                        '(uncommitted residue makes this requirement unselectable)')
        else:
            residue = [str(repo) for repo in repos if worktree_residue(repo)]
            if residue:
                note = f"{note}\n\nUncommitted work left in: {', '.join(residue)}"

        # Validate every lock before releasing any. Release before saving so a
        # crash leaves an active queue claim that the recovery command can find.
        for repo in repos:
            lock = repo / '.tasks/.lock'
            if lock.exists() and json.loads(lock.read_text()).get('token') != token:
                raise ValueError(f'lock ownership changed: {repo}')
        transition_at = datetime.now(timezone.utc).isoformat()
        holder = req['claim']['holder']
        req['state'] = state
        req['updated_at'] = transition_at
        if note:
            req['progress'] = note
        if evidence:
            req['evidence'] = evidence
        req.setdefault('transitions', []).append({
            'holder': holder,
            'state': state,
            'at': transition_at,
        })
        req.pop('claim')
        release(repos, token)
        save(path, data)
        return {'item': f"{charter['id']}/{req['id']}", 'state': state}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue', required=True, type=Path)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('validate')
    for command in ('next', 'claim'):
        cmd = sub.add_parser(command)
        cmd.add_argument('--worker', required=True)
        if command == 'claim':
            cmd.add_argument('--holder', required=True)
    cmd = sub.add_parser('check-exit')
    cmd.add_argument('--holder', required=True)
    cmd = sub.add_parser('finish')
    cmd.add_argument('--token', required=True)
    cmd.add_argument('--state', choices=['done', 'ready', 'blocked'], required=True)
    cmd.add_argument('--note')
    cmd.add_argument('--evidence', action='append', default=[])
    cmd = sub.add_parser('recover')
    group = cmd.add_mutually_exclusive_group(required=True)
    group.add_argument('--token')
    group.add_argument('--item', help="charter/requirement, e.g. HMT-C3/R1")
    cmd.add_argument('--reason', required=True)
    cmd = sub.add_parser('task')
    cmd.add_argument('--token', required=True)
    cmd.add_argument('--repo', type=Path, required=True)
    cmd.add_argument('--id', required=True)
    cmd.add_argument('--title', required=True)
    cmd = sub.add_parser('report')
    cmd.add_argument('--worker', required=True)
    cmd.add_argument('--holder', required=True)
    cmd.add_argument('--state', choices=sorted(REPORT_STATES), required=True)
    cmd.add_argument('--item')
    cmd.add_argument('--summary', required=True)
    cmd.add_argument('--evidence', action='append', default=[])
    cmd.add_argument('--continuation')
    cmd = sub.add_parser('reports')
    cmd.add_argument('--since', help='exclusive ISO-8601 timestamp; reads across daily files')
    cmd = sub.add_parser('brief-window')
    cmd.add_argument('--previous-delivery', choices=['success', 'failed', 'unknown'], required=True)
    cmd.add_argument('--through', required=True,
                     help='inclusive ISO-8601 timestamp staged for next-run delivery reconciliation')
    try:
        print(json.dumps(run(p.parse_args()), indent=2))
    except (ValueError, KeyError, OSError, RuntimeError, TypeError) as error:
        print(f'Queue error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
