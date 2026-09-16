#!/usr/bin/env python3
"""Fresh charter queue: selection, atomic claims, task provenance and evidence closeout.

Only QUEUE.json is read; historical goal/task ledgers are never discovered.
Mutations use flock plus atomic replacement. Repository O_EXCL locks interoperate
with existing workers. No automatic stale-lock takeover is performed.
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

from repo_availability import worktree_residue

STATES = {"ready", "active", "blocked", "deferred", "done", "dropped"}


def read_queue(path):
    data = json.loads(path.read_text())
    if data.get("version") != 1 or not isinstance(data.get("charters"), list):
        raise ValueError("expected version 1 and charters list")
    ids = set()
    for charter in data["charters"]:
        cid = charter["id"]
        if cid in ids or not re.fullmatch(r"[A-Za-z0-9_-]+", cid):
            raise ValueError("duplicate or invalid charter id")
        ids.add(cid)
        if charter["status"] not in {"draft", "active", "paused", "closed"}:
            raise ValueError(f"{cid}: invalid charter status")
        if charter["status"] == "active" and not charter.get("authorized_by"):
            raise ValueError(f"{cid}: active charter has no authorization record")
        source = (path.parent / charter["path"]).resolve()
        contract = source.read_text()
        if charter.get("lane") not in {"research", "product", "any"}:
            raise ValueError(f"{cid}: invalid lane")
        requirements = charter["requirements"]
        rids = [r["id"] for r in requirements]
        if len(set(rids)) != len(rids) or not rids:
            raise ValueError(f"{cid}: duplicate or empty requirements")
        declared = re.findall(r"^### (R[1-9][0-9]*)\b", contract, re.M)
        if set(declared) != set(rids) or len(declared) != len(rids):
            raise ValueError(f"{cid}: requirement ids differ from charter headings")
        for req in requirements:
            if req["state"] not in STATES or not req.get("repos"):
                raise ValueError(f"{cid}/{req['id']}: invalid state or missing repositories")
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
    fd, name = tempfile.mkstemp(prefix=".queue-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def transaction(path):
    with (path.parent / ".charter-queue.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = read_queue(path)
        yield data


def repo_paths(path, req):
    return sorted({(path.parent / r).resolve() for r in req["repos"]})


def choose(path, data, lane, capabilities):
    skipped = []
    # Serial execution avoids simultaneous commits to shared portfolio state.
    active = [f"{c['id']}/{r['id']}" for c, r in rows(data) if r['state'] == 'active']
    if active:
        return None, [{"reason": "active claim requires completion or recovery", "items": active}]
    for charter, req in rows(data):
        key = f"{charter['id']}/{req['id']}"
        if charter['status'] != 'active' or req['state'] != 'ready':
            continue
        if lane and charter['lane'] not in {lane, 'any'}:
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


def run(args):
    path = args.queue.resolve()
    if args.command in {'next', 'validate', 'check-exit'}:
        data = read_queue(path)
        if args.command == 'validate':
            return {'valid': True, 'charters': len(data['charters'])}
        if args.command == 'check-exit':
            if any(r.get('claim', {}).get('holder') == args.holder for _, r in rows(data)):
                raise ValueError('unclosed requirement claim remains for this run')
            for repo in {repo for _, req in rows(data) for repo in repo_paths(path, req)}:
                lock = repo / '.tasks/.lock'
                if lock.exists() and json.loads(lock.read_text()).get('holder') == args.holder:
                    raise ValueError(f'unreleased repository lock: {repo}')
            return {'clean': True}
        selected, skipped = choose(path, data, args.lane, set(args.capability))
        return {'selected': describe(path, selected), 'skipped': skipped}
    with transaction(path) as data:
        if args.command == 'claim':
            if (path.parent / '.git').exists() and worktree_residue(path.parent):
                raise ValueError('commit or preserve control-repository changes before claiming')
            selected, skipped = choose(path, data, args.lane, set(args.capability))
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
        charter, req = owned(data, args.token)
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
        if state == 'done':
            for repo in repos:
                if worktree_residue(repo):
                    raise ValueError(f'commit the work before completion: {repo}')
        # Validate every lock before releasing any. Release before saving so a
        # crash leaves an active queue claim that the recovery command can find.
        for repo in repos:
            lock = repo / '.tasks/.lock'
            if lock.exists() and json.loads(lock.read_text()).get('token') != args.token:
                raise ValueError(f'lock ownership changed: {repo}')
        req['state'] = state
        req['updated_at'] = datetime.now(timezone.utc).isoformat()
        if note:
            req['progress'] = note
        if evidence:
            req['evidence'] = evidence
        req.pop('claim')
        release(repos, args.token)
        save(path, data)
        return {'item': f"{charter['id']}/{req['id']}", 'state': state}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--queue', required=True, type=Path)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('validate')
    for command in ('next', 'claim'):
        cmd = sub.add_parser(command)
        cmd.add_argument('--lane')
        cmd.add_argument('--capability', action='append', default=[])
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
    cmd.add_argument('--token', required=True)
    cmd.add_argument('--reason', required=True)
    cmd = sub.add_parser('task')
    cmd.add_argument('--token', required=True)
    cmd.add_argument('--repo', type=Path, required=True)
    cmd.add_argument('--id', required=True)
    cmd.add_argument('--title', required=True)
    try:
        print(json.dumps(run(p.parse_args()), indent=2))
    except (ValueError, KeyError, OSError, RuntimeError, TypeError) as error:
        print(f'Queue error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
