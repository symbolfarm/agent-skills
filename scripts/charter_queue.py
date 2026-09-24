#!/usr/bin/env python3
"""Fresh charter queue, worker profiles, claims, close-outs and report windows.

Only QUEUE.json and WORKERS.json provide execution state; historical goal/task
ledgers are never discovered. Mutations use flock plus atomic replacement.
Repository O_EXCL locks interoperate with existing workers. No automatic
stale-lock takeover is performed: an expired claim is reported with the command
that clears it, never seized. Every queue mutation is committed here, inside the
queue lock and limited to QUEUE.json, so concurrent workers never sweep each
other's changes into a portfolio commit.
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
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from zoneinfo import ZoneInfo

from repo_availability import worktree_residue

STATES = {"ready", "active", "blocked", "deferred", "done", "dropped"}
SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")
RUN_ID = re.compile(r"[A-Za-z0-9_.:-]+")
REPORT_STATES = {"no-op", "advanced", "completed", "blocked", "failed"}
REPORT_RECORD = re.compile(r"<!-- worker-closeout: (\{.*\}) -->")

# Detached jobs. Live status lives in gitignored `<portfolio>/.jobs/<id>.json`,
# written by the runner process; the queue keeps the durable record. A runner
# refreshes its heartbeat every poll, so a job whose container is gone reads as
# lost once the heartbeat is stale rather than running forever.
JOBS_DIR = ".jobs"
JOB_POLL_SECONDS = float(os.environ.get("CHARTER_JOB_POLL", "5"))
JOB_GRACE_SECONDS = float(os.environ.get("CHARTER_JOB_GRACE", "30"))
JOB_STALE_SECONDS = float(os.environ.get("CHARTER_JOB_STALE", "180"))
# A resumable claim is kept this long past its job's deadline, so the worker's
# next scheduled run finds it unexpired.
JOB_CLAIM_MARGIN = timedelta(hours=24)

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
    health_sources = set()
    for worker in data["workers"]:
        if not isinstance(worker, dict):
            raise ValueError("WORKERS.json: every worker must be an object")
        required_fields = {"id", "holder_prefix", "capabilities", "wind_down",
                           "report_sink", "health"}
        if not required_fields.issubset(worker) or set(worker) - (
                required_fields | {"legacy_holder_prefixes", "max_job_hours"}):
            raise ValueError("WORKERS.json: unknown or missing worker field")
        worker_id = worker.get("id")
        if not isinstance(worker_id, str) or not SAFE_ID.fullmatch(worker_id) or worker_id in workers:
            raise ValueError("WORKERS.json: duplicate or invalid worker id")
        prefix = worker.get("holder_prefix")
        if (not isinstance(prefix, str) or not SAFE_ID.fullmatch(prefix)
                or prefix in prefixes):
            raise ValueError(f"WORKERS.json: {worker_id} has duplicate or invalid holder_prefix")
        legacy_prefixes = worker.get("legacy_holder_prefixes", [])
        if (not isinstance(legacy_prefixes, list)
                or len(legacy_prefixes) != len(set(legacy_prefixes))
                or not all(isinstance(item, str) and SAFE_ID.fullmatch(item)
                           for item in legacy_prefixes)
                or prefix in legacy_prefixes
                or prefixes.intersection(legacy_prefixes)):
            raise ValueError(f"WORKERS.json: {worker_id} has invalid legacy_holder_prefixes")
        prefixes.add(prefix)
        prefixes.update(legacy_prefixes)
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
        max_job_hours = worker.get("max_job_hours")
        if max_job_hours is not None and (type(max_job_hours) not in (int, float)
                                          or max_job_hours <= 0):
            raise ValueError(f"WORKERS.json: {worker_id} has invalid max_job_hours")
        safe_relative(path.parent, worker.get("report_sink", ""),
                      f"WORKERS.json: {worker_id} report_sink")
        health = worker.get("health", {})
        if not isinstance(health, dict):
            raise ValueError(f"WORKERS.json: {worker_id} has invalid health")
        if health.get("kind") == "hermes-cron":
            if (set(health) != {"kind", "job_id"}
                    or not isinstance(health.get("job_id"), str)
                    or not health["job_id"].strip()
                    or health["job_id"] != health["job_id"].strip()):
                raise ValueError(f"WORKERS.json: {worker_id} health needs job_id")
            health_source = ("hermes-cron", health["job_id"])
        elif health.get("kind") == "file":
            if set(health) != {"kind", "path"}:
                raise ValueError(f"WORKERS.json: {worker_id} health needs only path")
            health_path = safe_relative(path.parent, health.get("path", ""),
                                        f"WORKERS.json: {worker_id} health path")
            health_source = ("file", str(health_path))
        else:
            raise ValueError(f"WORKERS.json: {worker_id} has invalid health kind")
        if health_source in health_sources:
            raise ValueError(f"WORKERS.json: {worker_id} reuses another worker's health source")
        health_sources.add(health_source)
        workers[worker_id] = worker
    if not workers:
        raise ValueError("WORKERS.json: at least one worker is required")
    return data, workers


def read_queue(path, workers):
    data = json.loads(path.read_text())
    if data.get("version") != 2 or not isinstance(data.get("charters"), list):
        raise ValueError("expected version 2 and charters list")
    allowed_prefixes = tuple(
        prefix + "-"
        for worker in workers.values()
        for prefix in [worker["holder_prefix"], *worker.get("legacy_holder_prefixes", [])])
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
        gpu_hours = charter.get("gpu_hours")
        if gpu_hours is not None and (type(gpu_hours) not in (int, float) or gpu_hours < 0):
            raise ValueError(f"{cid}: gpu_hours must be a non-negative number")
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
            jobs = req.get("jobs", [])
            if not isinstance(jobs, list) or not all(
                    isinstance(job, dict) and SAFE_ID.fullmatch(str(job.get("id", "")))
                    and RUN_ID.fullmatch(str(job.get("holder", ""))) for job in jobs):
                raise ValueError(f"{cid}/{req['id']}: invalid jobs record")
            transitions = req.get("transitions", [])
            if not isinstance(transitions, list):
                raise ValueError(f"{cid}/{req['id']}: transitions must be a list")
            for transition in transitions:
                if (not isinstance(transition, dict)
                        or set(transition) != {"holder", "state", "at"}
                        or not RUN_ID.fullmatch(transition.get("holder", ""))
                        or transition.get("state") not in {"ready", "blocked", "done", "handover"}):
                    raise ValueError(f"{cid}/{req['id']}: invalid transition record")
                # A transition must be attributable to a configured worker, so a
                # close-out cannot be justified by a hand-written holder string.
                if not transition["holder"].startswith(tuple(allowed_prefixes)):
                    raise ValueError(f"{cid}/{req['id']}: transition holder is not a known worker")
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


def awaiting_close(data):
    """Active charters with no open requirement. Workers skip them; closing is
    a joint decision at portfolio review, so the helper reports rather than acts."""
    return [c['id'] for c in data['charters'] if c['status'] == 'active'
            and all(r['state'] in {'done', 'dropped'} for r in c['requirements'])]


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


def queue_dirty(path):
    """True when QUEUE.json differs from the portfolio's HEAD."""
    if not (path.parent / '.git').exists():
        return False
    result = subprocess.run(['git', '-C', str(path.parent), 'status', '--porcelain', '--', path.name],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or 'git status failed')
    return bool(result.stdout.strip())


def commit_queue(path, message):
    """Commit QUEUE.json alone, under the queue lock the caller already holds.

    The pathspec makes this an --only commit: whatever else another worker has
    staged or left in the portfolio stays out of it. A worker's own `git commit`
    elsewhere in the portfolio can hold the index lock briefly, so that one
    failure is retried; any other failure is an error.
    """
    if not queue_dirty(path):
        return None
    for _ in range(20):
        result = subprocess.run(['git', '-C', str(path.parent), 'commit', '-q', '-m', message,
                                 '--', path.name], capture_output=True, text=True)
        if result.returncode == 0:
            return subprocess.check_output(['git', '-C', str(path.parent), 'rev-parse', '--short',
                                            'HEAD'], text=True).strip()
        if 'index.lock' not in result.stderr:
            break
        time.sleep(0.5)
    raise RuntimeError('queue transition saved but not committed; the next helper mutation '
                       f'commits it: {result.stderr.strip()}')


def job_file(path, job_id):
    return path.parent / JOBS_DIR / f"{job_id}.json"


def job_live(path, job):
    """The job's current status from its live file: running, exited,
    killed-budget, killed-signal or lost, with timing where known."""
    live_path = job_file(path, job['id'])
    if not live_path.exists():
        return {'status': 'lost'}
    live = json.loads(live_path.read_text())
    if live.get('status') in (None, 'starting', 'running'):
        beat = live.get('heartbeat') or live.get('started_at')
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(beat)).total_seconds()
        if age > JOB_STALE_SECONDS:
            return {**live, 'status': 'lost', 'ended_at': beat}
        return {**live, 'status': 'running'}
    return live


def settle_jobs(path, req):
    """Copy finished jobs' outcomes into the durable queue record.

    Returns True while any job is still running. A lost job is charged up to its
    last heartbeat, or its whole reservation when nothing is known.
    """
    running = False
    for job in req.get('jobs', []):
        if 'hours_used' in job:
            continue
        live = job_live(path, job)
        if live['status'] == 'running':
            running = True
            continue
        job['status'] = live['status']
        if 'exit_code' in live:
            job['exit_code'] = live['exit_code']
        if live.get('ended_at'):
            job['ended_at'] = live['ended_at']
            elapsed = (datetime.fromisoformat(live['ended_at'])
                       - datetime.fromisoformat(job['started_at'])).total_seconds() / 3600
            job['hours_used'] = round(max(elapsed, 0.0), 4)
        else:
            job['hours_used'] = job['hours_reserved']
    return running


def gpu_hours_committed(path, charter):
    """Hours used by finished jobs plus hours reserved by unfinished ones."""
    total = 0.0
    for req in charter['requirements']:
        for job in req.get('jobs', []):
            total += job.get('hours_used', job['hours_reserved'])
    return total


def job_start(path, workers, data, args):
    token = resolve_token(data, args)
    charter, req = owned(data, token)
    holder = req['claim']['holder']
    worker = next((w for w in workers.values() if holder.startswith(w['holder_prefix'] + '-')), None)
    if worker is None or worker.get('max_job_hours') is None:
        raise ValueError('this worker profile has no max_job_hours; it cannot run detached jobs')
    hours = args.hours
    if not hours > 0 or hours > worker['max_job_hours']:
        raise ValueError(f"--hours must be above 0 and at most {worker['max_job_hours']} "
                         f"(the worker's max_job_hours)")
    if charter.get('gpu_hours') is None:
        raise ValueError(f"{charter['id']} has no gpu_hours budget; the user sets one at authorization")
    settle_jobs(path, req)
    remaining = charter['gpu_hours'] - gpu_hours_committed(path, charter)
    if hours > remaining + 1e-9:
        raise ValueError(f"{charter['id']} has {remaining:.2f} of {charter['gpu_hours']} GPU-hours "
                         f"left; --hours {hours} exceeds it")
    repos = repo_paths(path, req)
    cwd = (args.cwd or repos[0]).resolve()
    if cwd not in repos:
        raise ValueError('--cwd must be a claimed repository')
    log = (cwd / args.log).resolve()
    if cwd not in log.parents:
        raise ValueError('--log must stay inside the working repository')
    command = list(args.job_command)
    if command[:1] == ['--']:
        command = command[1:]
    if not command:
        raise ValueError('a job needs a command after --')
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=hours)
    job_id = f"job-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
    live = {'id': job_id, 'token': token, 'holder': holder,
            'run': os.environ.get('AGENT_RUN_ID'), 'status': 'starting',
            'command': command, 'cwd': str(cwd), 'log': str(log),
            'started_at': now.isoformat(), 'deadline': deadline.isoformat(),
            'heartbeat': now.isoformat()}
    atomic_text(job_file(path, job_id), json.dumps(live, indent=2) + '\n')
    record = {'id': job_id, 'holder': holder, 'command': shlex.join(command),
              'cwd': os.path.relpath(cwd, path.parent), 'log': os.path.relpath(log, path.parent),
              'started_at': now.isoformat(), 'deadline': deadline.isoformat(),
              'hours_reserved': hours}
    req.setdefault('jobs', []).append(record)
    claim_expiry = deadline + JOB_CLAIM_MARGIN
    if datetime.fromisoformat(req['claim']['expires_at']) < claim_expiry:
        req['claim']['expires_at'] = claim_expiry.isoformat()
    save(path, data)
    item = f"{charter['id']}/{req['id']}"
    commit = commit_queue(path, f"{item}: job {job_id} ({hours} GPU-hours) by {holder}")
    # The runner gets its own session so it outlives the agent's tool call and
    # the agent process; the container keeps running until it finishes.
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--queue', str(path),
                      'job-run', job_id], start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    return {'job': record, 'item': item, 'commit': commit,
            'gpu_hours_left': round(remaining - hours, 4)}


def job_run(path, job_id):
    """Runs one job to completion or its deadline. Not called by agents."""
    live_path = job_file(path, job_id)
    live = json.loads(live_path.read_text())
    deadline = datetime.fromisoformat(live['deadline'])
    log = Path(live['log'])
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('ab') as out:
        child = subprocess.Popen(live['command'], cwd=live['cwd'], stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    stopping = {'status': None}

    def stop(status):
        if stopping['status'] is None:
            stopping['status'] = status
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            stopping['at'] = time.monotonic()

    signal.signal(signal.SIGTERM, lambda *_: stop('killed-signal'))
    live.update(status='running', pid=child.pid)
    atomic_text(live_path, json.dumps(live, indent=2) + '\n')
    while child.poll() is None:
        if datetime.now(timezone.utc) >= deadline:
            stop('killed-budget')
        if stopping['status'] and time.monotonic() - stopping['at'] > JOB_GRACE_SECONDS:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        live['heartbeat'] = datetime.now(timezone.utc).isoformat()
        atomic_text(live_path, json.dumps(live, indent=2) + '\n')
        time.sleep(JOB_POLL_SECONDS)
    live.update(status=stopping['status'] or 'exited', exit_code=child.returncode,
                ended_at=datetime.now(timezone.utc).isoformat())
    atomic_text(live_path, json.dumps(live, indent=2) + '\n')
    return {'job': job_id, 'status': live['status'], 'exit_code': child.returncode}


def jobs_view(path, data, run_id=None):
    views = []
    for charter, req in rows(data):
        for job in req.get('jobs', []):
            live = job_live(path, job) if 'hours_used' not in job else job
            if run_id and live.get('run') != run_id:
                continue
            views.append({'item': f"{charter['id']}/{req['id']}", 'id': job['id'],
                          'holder': job['holder'], 'status': live.get('status'),
                          'deadline': job['deadline'], 'log': job['log'],
                          'exit_code': live.get('exit_code')})
    return views


def wait_for_jobs(path, workers, run_id):
    """Blocks while any job started by this container run is still running."""
    while True:
        running = [v for v in jobs_view(path, read_queue(path, workers), run_id)
                   if v['status'] == 'running']
        if not running:
            return {'run': run_id, 'running': 0}
        time.sleep(max(JOB_POLL_SECONDS, 1))


def has_job_by(req, holder):
    return any(job['holder'] == holder for job in req.get('jobs', []))


def repo_paths(path, req):
    return sorted({(path.parent / r).resolve() for r in req["repos"]})


def choose(path, data, worker):
    skipped = []
    worker_id = worker["id"]
    capabilities = set(worker["capabilities"])
    prefixes = tuple(p + '-' for p in [worker['holder_prefix'], *worker.get('legacy_holder_prefixes', [])])
    # Workers run concurrently, one claim each. Another worker's claim blocks
    # only the repositories it locked, which the per-repository check below
    # enforces; it is listed so a stalled one stays visible. A worker whose own
    # earlier claim is still open gets nothing new: that claim is finished or
    # recovered first. An expired claim is reported with the command that
    # clears it, never seized — its worker may still be running.
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
    mine = [entry for entry in active if (entry["holder"] or "").startswith(prefixes)]
    others = [entry for entry in active if entry not in mine]
    if mine:
        # A claim left open for a detached job is resumed by the same worker's
        # next run once the job has finished; anything else needs recovery.
        for entry in mine:
            charter, req = next((c, r) for c, r in rows(data)
                                if f"{c['id']}/{r['id']}" == entry["item"])
            if req.get('jobs') and has_job_by(req, entry["holder"]):
                if any(job_live(path, job)['status'] == 'running'
                       for job in req['jobs'] if 'hours_used' not in job):
                    return None, [{"reason": "own detached job still running",
                                   "stalled": False, "items": [entry]}]
                skipped.extend({"reason": "another worker's active claim", "stalled": o["expired"],
                                "items": [o]} for o in others)
                return (charter, req), skipped
        return None, [{"reason": "active claim requires completion or recovery",
                       "stalled": any(entry["expired"] for entry in mine),
                       "items": mine}]
    if others:
        skipped.append({"reason": "another worker's active claim",
                        "stalled": any(entry["expired"] for entry in others),
                        "items": others})
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
    # A claim this run left open for its own detached job is a deliberate
    # handover, not a leak: the worker's next run resumes it.
    held = [r for _, r in rows(data) if r.get('claim', {}).get('holder') == holder]
    if any(not has_job_by(r, holder) for r in held):
        raise ValueError('unclosed requirement claim remains for this run')
    kept = {repo for r in held for repo in repo_paths(path, r)}
    for repo in {repo for _, req in rows(data) for repo in repo_paths(path, req)} - kept:
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
    # A floor bounds the window only while no delivery has ever been confirmed.
    # Once anything is delivered, the confirmed cursor is the only lower bound:
    # clamping against the floor then would silently drop unsent material.
    floor = aware_timestamp(args.earliest, '--earliest') if args.earliest else None
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
    if delivered:
        since = aware_timestamp(delivered, 'briefing cursor')
    else:
        since = floor
    if since is not None and through < since:
        raise ValueError('--through precedes the briefing window start')
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
        'earliest_floor': floor.isoformat() if floor else None,
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
    if queue_dirty(path):
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
        if not matching and args.state == 'advanced' and has_job_by(known_items[item], args.holder):
            matching = [True]
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
    if args.command == 'job-run':
        return job_run(path, args.job_id)
    if args.command in {'next', 'validate', 'check-exit', 'reports', 'jobs'}:
        data = read_queue(path, workers)
        if args.command == 'jobs':
            if args.wait:
                if not args.run:
                    raise ValueError('--wait needs --run')
                return wait_for_jobs(path, workers, args.run)
            return {'jobs': jobs_view(path, data, args.run)}
        if args.command == 'validate':
            return {'valid': True, 'charters': len(data['charters']), 'workers': len(workers),
                    'awaiting_close': awaiting_close(data)}
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
        return {'selected': describe(path, selected), 'skipped': skipped,
                'awaiting_close': awaiting_close(data)}
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
            if queue_dirty(path):
                raise ValueError('QUEUE.json has uncommitted changes; commit or preserve them before claiming')
            selected, skipped = choose(path, data, worker)
            if selected is None:
                return {'selected': None, 'skipped': skipped}
            charter, req = selected
            token = uuid.uuid4().hex
            now = datetime.now(timezone.utc)
            claim = {'holder': args.holder, 'token': token, 'acquired_at': now.isoformat(),
                     'expires_at': (now + timedelta(hours=4)).isoformat(),
                     'item': f"{charter['id']}/{req['id']}"}
            if req['state'] == 'active':
                # Resume after a detached job: the locks move to the new claim.
                previous = req['claim']
                repos = repo_paths(path, req)
                for repo in repos:
                    lock = repo / '.tasks/.lock'
                    if not lock.exists() or json.loads(lock.read_text()).get('token') != previous['token']:
                        raise ValueError(f'lock ownership changed: {repo}')
                settle_jobs(path, req)
                for repo in repos:
                    atomic_text(repo / '.tasks/.lock', json.dumps(claim))
                req.setdefault('transitions', []).append(
                    {'holder': previous['holder'], 'state': 'handover', 'at': now.isoformat()})
                req['claim'] = claim
                save(path, data)
                commit = commit_queue(path, f"{claim['item']}: resume by {args.holder} "
                                            f"after {previous['holder']}'s job")
                return {'selected': describe(path, selected), 'resumed_from': previous['holder'],
                        'skipped': skipped, 'awaiting_close': awaiting_close(data),
                        'commit': commit}
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
            commit = commit_queue(path, f"{claim['item']}: claim by {args.holder}")
            return {'selected': describe(path, selected), 'skipped': skipped,
                    'awaiting_close': awaiting_close(data), 'commit': commit}
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
            commit = commit_queue(path, f"{parent}: task {args.id} by {req['claim']['holder']}")
            return {'task': str(dest), 'parent': parent, 'commit': commit}
        if args.command in ('job-start',):
            return job_start(path, workers, data, args)
        recovering = args.command == 'recover'
        if settle_jobs(path, req):
            raise ValueError('a detached job on this requirement is still running; wait for it '
                             'or stop it before this transition')
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
        item = f"{charter['id']}/{req['id']}"
        verb = f"recover {holder}'s claim" if recovering else f"{state} by {holder}"
        commit = commit_queue(path, f"{item}: {verb}")
        return {'item': item, 'state': state, 'commit': commit}


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
    cmd = sub.add_parser('job-start', help='run a long job detached from this session')
    cmd.add_argument('--token', required=True)
    cmd.add_argument('--hours', type=float, required=True,
                     help="GPU-hours reserved; the job is stopped at this deadline")
    cmd.add_argument('--log', required=True, help='log path inside the working repository')
    cmd.add_argument('--cwd', type=Path, help='claimed repository to run in (default: first)')
    cmd.add_argument('job_command', nargs=argparse.REMAINDER, help='-- then the command')
    cmd = sub.add_parser('job-run', help=argparse.SUPPRESS)
    cmd.add_argument('job_id')
    cmd = sub.add_parser('jobs')
    cmd.add_argument('--run', help='only jobs started in this container run (AGENT_RUN_ID)')
    cmd.add_argument('--wait', action='store_true', help='block until none of them is running')
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
    cmd.add_argument('--earliest', help='lower bound used only when no delivery has ever been '
                                        'confirmed, so an unconsummated cursor cannot replay history')
    try:
        print(json.dumps(run(p.parse_args()), indent=2))
    except (ValueError, KeyError, OSError, RuntimeError, TypeError) as error:
        print(f'Queue error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
