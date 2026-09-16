import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/charter_queue.py'
WORKERS_SCHEMA = Path(__file__).resolve().parents[1] / (
    'skills/charter-cycle/assets/workers.schema.json')


class CharterQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.portfolio = self.root / 'portfolio'
        self.portfolio.mkdir()
        self.repo = self.make_repo('research')
        self.queue = self.portfolio / 'QUEUE.json'
        self.workers = self.portfolio / 'WORKERS.json'
        self.workers.write_text(json.dumps({
            'version': 1,
            'timezone': 'Australia/Adelaide',
            'workers': [
                {
                    'id': 'research-worker',
                    'holder_prefix': 'research-worker',
                    'capabilities': ['general'],
                    'wind_down': {'minutes': 50, 'reserve_minutes': 10},
                    'report_sink': '.briefing/daily',
                    'health': {'kind': 'file', 'path': '.briefing/health/research-worker.json'},
                },
                {
                    'id': 'product-worker',
                    'holder_prefix': 'product-worker',
                    'capabilities': ['general', 'network'],
                    'wind_down': {'minutes': 40, 'reserve_minutes': 10},
                    'report_sink': '.briefing/daily',
                    'health': {'kind': 'hermes-cron', 'job_id': 'fixture-job'},
                },
            ],
        }))
        (self.portfolio / 'charter.md').write_text('# Question\n\n### R1 — Compare\n\n### R2 — Explain\n')
        self.data = {'version': 2, 'charters': [{
            'id': 'C-001', 'path': 'charter.md', 'status': 'active',
            'authorized_by': 'Fixture user, explicit test authorization',
            'eligible_workers': ['research-worker'],
            'requirements': [
                {'id': 'R1', 'state': 'ready', 'repos': ['../research'], 'requires': ['general']},
                {'id': 'R2', 'state': 'ready', 'repos': ['../research'], 'depends_on': ['R1']}
            ]}]}
        self.write()

    def make_repo(self, name):
        repo = self.root / name
        repo.mkdir()
        (repo / '.gitignore').write_text('.tasks/.lock\n')
        for args in (['init', '-q'], ['config', 'user.email', 'test@example.invalid'],
                     ['config', 'user.name', 'Test'], ['add', '.'], ['commit', '-qm', 'initial']):
            subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
        return repo

    def write(self):
        self.queue.write_text(json.dumps(self.data))

    def cmd(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(SCRIPT), '--queue', str(self.queue), *args],
                           text=True, capture_output=True)
        self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return json.loads(r.stdout) if ok else r.stderr

    def claim(self, holder='research-worker-run-a'):
        return self.cmd('claim', '--worker', 'research-worker', '--holder', holder)[
            'selected']['requirement']['claim']['token']

    def test_empty_queue_never_discovers_legacy_work(self):
        self.data['charters'] = []
        self.write()
        (self.portfolio / 'GOALS.md').write_text('## Queue\n- **G-001** `research` — old work\n')
        self.assertIsNone(self.cmd('next', '--worker', 'research-worker')['selected'])

    def test_draft_deferral_worker_capability_and_dependency_gates(self):
        self.assertIsNone(self.cmd('next', '--worker', 'product-worker')['selected'])
        self.data['charters'][0]['requirements'][0]['requires'] = ['network']
        self.write()
        self.cmd('validate', ok=False)
        self.data['charters'][0]['requirements'][0]['requires'] = ['general']
        self.data['charters'][0]['requirements'][0]['state'] = 'deferred'
        self.write()
        self.assertIsNone(self.cmd('next', '--worker', 'research-worker')['selected'])
        self.data['charters'][0]['status'] = 'draft'
        self.data['charters'][0]['requirements'][0]['state'] = 'ready'
        self.write()
        self.assertIsNone(self.cmd('next', '--worker', 'research-worker')['selected'])

    def test_done_needs_evidence_and_unlocks_dependents(self):
        token = self.claim()
        self.cmd('check-exit', '--holder', 'research-worker-run-a', ok=False)
        self.cmd('finish', '--token', token, '--state', 'done', ok=False)
        self.assertTrue((self.repo / '.tasks/.lock').exists())
        self.cmd('finish', '--token', token, '--state', 'done', '--evidence', 'artifact: comparison established')
        self.assertFalse((self.repo / '.tasks/.lock').exists())
        self.cmd('check-exit', '--holder', 'research-worker-run-a')
        self.assertEqual(self.cmd('next', '--worker', 'research-worker')['selected']['item'], 'C-001/R2')

    def test_dirty_release_refused_and_never_touches_the_work(self):
        token = self.claim()
        work = self.repo / 'result.txt'
        work.write_text('incomplete result')
        self.cmd('finish', '--token', token, '--state', 'done', '--evidence', 'result', ok=False)
        self.cmd('finish', '--token', token, '--state', 'ready', '--note', 'Finish comparison', ok=False)
        self.assertEqual(work.read_text(), 'incomplete result')
        subprocess.run(['git', '-C', str(self.repo), 'add', '-A'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-qm', 'partial'], check=True, capture_output=True)
        self.cmd('finish', '--token', token, '--state', 'ready', '--note', 'Finish comparison')
        self.assertEqual(self.cmd('next', '--worker', 'research-worker')['selected']['item'], 'C-001/R1')
        self.cmd('check-exit', '--holder', 'research-worker-run-a')

    def test_task_inherits_parent_and_cannot_escape_repository(self):
        token = self.claim()
        result = self.cmd('task', '--token', token, '--repo', str(self.repo), '--id', 'EXP-1', '--title', 'Compare')
        self.assertIn('Parent: C-001/R1', Path(result['task']).read_text())
        self.assertTrue(json.loads(self.queue.read_text())['charters'][0]['requirements'][0]['tasks'])
        self.cmd('task', '--token', token, '--repo', str(self.root), '--id', 'EXP-2', '--title', 'bad', ok=False)
        self.cmd('task', '--token', token, '--repo', str(self.repo), '--id', '../escape', '--title', 'bad', ok=False)

    def test_concurrent_claims_have_one_winner(self):
        argv = [sys.executable, str(SCRIPT), '--queue', str(self.queue), 'claim',
                '--worker', 'research-worker', '--holder']
        ps = [subprocess.Popen([*argv, holder], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
              for holder in ['research-worker-run-a', 'research-worker-run-b']]
        results = [p.communicate() for p in ps]
        for p, (_, stderr) in zip(ps, results):
            self.assertEqual(p.returncode, 0, stderr)
        self.assertEqual(sum(json.loads(out)['selected'] is not None for out, _ in results), 1)

    def test_other_lock_blocks_and_recovery_never_deletes_changed_lock(self):
        token = self.claim()
        lock = self.repo / '.tasks/.lock'
        other = {'holder': 'another worker', 'token': 'other'}
        lock.write_text(json.dumps(other))
        self.cmd('recover', '--token', token, '--reason', 'worker stopped', ok=False)
        self.assertEqual(json.loads(lock.read_text()), other)
        self.cmd('check-exit', '--holder', 'research-worker-run-a', ok=False)

    def test_dirty_repo_skips_to_clean_requirement(self):
        clean = self.make_repo('clean')
        (self.repo / 'residue').write_text('keep')
        self.data['charters'][0]['requirements'][1]['repos'] = ['../clean']
        self.data['charters'][0]['requirements'][1]['depends_on'] = []
        self.write()
        self.assertEqual(self.cmd('next', '--worker', 'research-worker')['selected']['item'], 'C-001/R2')
        self.assertTrue((self.repo / 'residue').exists())

    def test_unapproved_mismatched_or_cyclic_queue_is_error(self):
        self.data['charters'][0]['authorized_by'] = None
        self.write()
        self.cmd('validate', ok=False)
        self.data['charters'][0]['authorized_by'] = 'fixture user'
        self.data['charters'][0]['requirements'][0]['depends_on'] = ['R2']
        self.write()
        self.cmd('validate', ok=False)
        self.data['charters'][0]['requirements'][0]['depends_on'] = []
        self.write()
        (self.portfolio / 'charter.md').write_text('### R3 — wrong requirement\n')
        self.cmd('validate', ok=False)

    def test_existing_lock_prevents_multirepo_claim_without_taking_other_locks(self):
        # Pre-existing lock blocks the item without touching either repository.
        clean = self.make_repo('another')
        (self.repo / '.tasks').mkdir()
        (self.repo / '.tasks/.lock').write_text('{}')
        self.data['charters'][0]['requirements'][0]['repos'] = ['../another', '../research']
        self.write()
        self.assertIsNone(self.cmd(
            'claim', '--worker', 'research-worker', '--holder', 'research-worker-run-a')['selected'])
        self.assertFalse((clean / '.tasks/.lock').exists())

    def test_control_repository_must_be_clean_before_claim(self):
        (self.portfolio / '.gitignore').write_text('.charter-queue.lock\n.queue-*\n')
        for args in (['init', '-q'], ['config', 'user.email', 'test@example.invalid'],
                     ['config', 'user.name', 'Test'], ['add', '.'], ['commit', '-qm', 'queue']):
            subprocess.run(['git', '-C', str(self.portfolio), *args], check=True, capture_output=True)
        (self.portfolio / 'uncommitted.md').write_text('another author')
        self.cmd('claim', '--worker', 'research-worker', '--holder',
                 'research-worker-run-a', ok=False)
        self.assertFalse((self.repo / '.tasks/.lock').exists())

    def test_complete_handoff_lifecycle_with_real_commits(self):
        (self.portfolio / '.gitignore').write_text(
            '.charter-queue.lock\n.queue-*\n.briefing/\n')
        for args in (['init', '-q'], ['config', 'user.email', 'test@example.invalid'],
                     ['config', 'user.name', 'Test'], ['add', '.'], ['commit', '-qm', 'queue']):
            subprocess.run(['git', '-C', str(self.portfolio), *args], check=True, capture_output=True)
        token = self.claim()
        for args in (['add', 'QUEUE.json'], ['commit', '-qm', 'claim']):
            subprocess.run(['git', '-C', str(self.portfolio), *args], check=True, capture_output=True)
        self.cmd('task', '--token', token, '--repo', str(self.repo), '--id', 'EXP-1', '--title', 'Compare')
        (self.repo / 'evidence.txt').write_text('baseline 0; intervention 1; fixture only')
        for args in (['add', '.'], ['commit', '-qm', 'comparison']):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)
        self.cmd('finish', '--token', token, '--state', 'done', '--evidence', 'research/evidence.txt: fixture comparison')
        self.assertIn('commit the control-repository transition', self.cmd(
            'report', '--worker', 'research-worker', '--holder', 'research-worker-run-a',
            '--state', 'completed', '--item', 'C-001/R1', '--summary', 'Comparison complete.',
            '--evidence', 'research/evidence.txt: fixture comparison', ok=False))
        for args in (['add', 'QUEUE.json'], ['commit', '-qm', 'close']):
            subprocess.run(['git', '-C', str(self.portfolio), *args], check=True, capture_output=True)
        self.cmd('check-exit', '--holder', 'research-worker-run-a')
        self.cmd(
            'report', '--worker', 'research-worker', '--holder', 'research-worker-run-a',
            '--state', 'completed', '--item', 'C-001/R1', '--summary', 'Comparison complete.',
            '--evidence', 'research/evidence.txt: fixture comparison')
        for repo in (self.repo, self.portfolio):
            status = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True)
            self.assertEqual(status, '')
        self.assertEqual(self.cmd('next', '--worker', 'research-worker')['selected']['item'], 'C-001/R2')

    def test_recovery_preserves_continuation_and_releases_own_locks(self):
        token = self.claim()
        self.cmd('recover', '--token', token, '--reason', 'Confirmed stopped; resume baseline')
        self.assertFalse((self.repo / '.tasks/.lock').exists())
        self.assertIn('resume baseline', self.cmd('next', '--worker', 'research-worker')['selected']['requirement']['progress'])

    def test_table_form_charter_declares_its_requirements(self):
        # The human-machine-teaming charters write requirements as a table, not
        # as headings. Both forms must load, or authorizing one of them makes the
        # whole queue unreadable for every worker.
        (self.portfolio / 'charter.md').write_text(
            '# Question\n\n## Requirements\n\n'
            '| # | Must be true |\n|---|---|\n'
            '| **R1** | Compare the baseline. |\n'
            '| **R2** | Explain the result. |\n')
        self.assertEqual(self.cmd('validate')['charters'], 1)
        self.assertEqual(self.cmd('next', '--worker', 'research-worker')['selected']['item'], 'C-001/R1')

    def test_charter_and_queue_requirement_ids_must_agree(self):
        (self.portfolio / 'charter.md').write_text('# Question\n\n### R1 — Compare\n')
        self.assertIn('differ from those the charter declares', self.cmd('validate', ok=False))
        # A discharged charter keys both a requirements table and an evidence
        # table by id, and may add a per-requirement heading. Ids recur; that is
        # the shape of a finished charter, not a disagreement with the queue.
        (self.portfolio / 'charter.md').write_text(
            '# Question\n\n| **R1** | Compare |\n| **R2** | Explain |\n\n'
            '## Discharge\n\n| **R1** | commit abc |\n| **R2** | commit def |\n\n'
            '### R1 — met\n\n### R2 — met\n')
        self.assertEqual(self.cmd('validate')['charters'], 1)

    def test_expired_claim_is_reported_as_a_stall_not_seized(self):
        self.claim()
        data = json.loads(self.queue.read_text())
        claim = data['charters'][0]['requirements'][0]['claim']
        claim['expires_at'] = '2000-01-01T00:00:00+00:00'
        self.queue.write_text(json.dumps(data))
        blocked = self.cmd('next', '--worker', 'research-worker')
        self.assertIsNone(blocked['selected'])
        entry = blocked['skipped'][0]
        self.assertTrue(entry['stalled'])
        self.assertTrue(entry['items'][0]['expired'])
        self.assertIn('recover --item C-001/R1', entry['items'][0]['clear_with'])
        self.assertTrue((self.repo / '.tasks/.lock').exists(), 'an expired claim must not be seized')

    def test_recover_by_item_without_the_token(self):
        self.claim()
        self.cmd('recover', '--item', 'C-001/R1', '--reason', 'Worker host rebooted; work preserved')
        self.assertFalse((self.repo / '.tasks/.lock').exists())
        self.assertEqual(self.cmd('next', '--worker', 'research-worker')['selected']['item'], 'C-001/R1')
        self.assertIn('no active claim', self.cmd('recover', '--item', 'C-001/R2',
                                                  '--reason', 'nothing there', ok=False))

    def test_blocked_records_the_residue_it_leaves(self):
        token = self.claim()
        (self.repo / 'scratch.txt').write_text('half-finished\n')
        self.cmd('finish', '--token', token, '--state', 'blocked', '--note', 'Needs a ruling on scope')
        progress = json.loads(self.queue.read_text())['charters'][0]['requirements'][0]['progress']
        self.assertIn('Uncommitted work left in', progress)

    def test_claim_preserves_the_queue_file_mode(self):
        self.queue.chmod(0o644)
        self.claim()
        self.assertEqual(self.queue.stat().st_mode & 0o777, 0o644)

    def test_worker_profiles_and_charter_eligibility_fail_closed(self):
        self.assertEqual(json.loads(WORKERS_SCHEMA.read_text())['title'],
                         'Scheduled charter worker profiles')
        self.assertIn('unknown worker', self.cmd(
            'next', '--worker', 'missing', ok=False))
        self.data['charters'][0]['eligible_workers'] = []
        self.write()
        self.assertIn('eligible_workers', self.cmd('validate', ok=False))
        self.data['charters'][0]['status'] = 'draft'
        self.write()
        self.assertEqual(self.cmd('validate')['charters'], 1)
        self.data['charters'][0]['status'] = 'active'
        self.data['charters'][0]['eligible_workers'] = ['missing']
        self.write()
        self.assertIn('unknown eligible worker', self.cmd('validate', ok=False))

    def test_worker_paths_and_run_ids_fail_closed(self):
        workers = json.loads(self.workers.read_text())
        workers['unexpected'] = True
        self.workers.write_text(json.dumps(workers))
        self.assertIn('unknown top-level field', self.cmd('validate', ok=False))
        workers.pop('unexpected')
        workers['workers'][0]['wind_down']['minutes'] = True
        self.workers.write_text(json.dumps(workers))
        self.assertIn('invalid wind_down', self.cmd('validate', ok=False))
        workers['workers'][0]['wind_down']['minutes'] = 50
        workers['workers'][0]['report_sink'] = ''
        self.workers.write_text(json.dumps(workers))
        self.assertIn('non-empty relative path', self.cmd('validate', ok=False))
        workers['workers'][0]['report_sink'] = '../outside'
        self.workers.write_text(json.dumps(workers))
        self.assertIn('stay inside the portfolio', self.cmd('validate', ok=False))
        self.workers.write_text(json.dumps({
            **workers,
            'workers': [{**workers['workers'][0], 'report_sink': '.briefing/daily'},
                        workers['workers'][1]],
        }))
        self.assertIn('holder must begin', self.cmd(
            'report', '--worker', 'research-worker', '--holder', 'research-worker-bad id',
            '--state', 'no-op', '--summary', 'No work.', ok=False))

    def test_report_is_structured_atomic_and_deduplicated(self):
        result = self.cmd(
            'report', '--worker', 'research-worker', '--holder', 'research-worker-001',
            '--state', 'no-op', '--summary', 'No eligible authorized requirement.')
        report = Path(result['report'])
        text = report.read_text()
        self.assertIn('Worker close-outs', text)
        self.assertIn('research-worker-001', text)
        self.assertIn('No eligible authorized requirement.', text)
        self.cmd(
            'report', '--worker', 'research-worker', '--holder', 'research-worker-001',
            '--state', 'no-op', '--summary', 'Duplicate', ok=False)

    def test_report_refuses_an_unclosed_claim(self):
        self.claim(holder='research-worker-active')
        self.assertIn('unclosed requirement claim', self.cmd(
            'report', '--worker', 'research-worker', '--holder', 'research-worker-active',
            '--state', 'advanced', '--item', 'C-001/R1', '--summary', 'Partial work.',
            '--continuation', 'Finish it.', ok=False))

    def test_report_state_must_match_the_queue(self):
        self.assertIn('unknown report item', self.cmd(
            'report', '--worker', 'research-worker', '--holder', 'research-worker-unknown',
            '--state', 'completed', '--item', 'C-999/R9', '--summary', 'Done.',
            '--evidence', 'commit abc', ok=False))
        self.assertIn('matching durable transition', self.cmd(
            'report', '--worker', 'research-worker', '--holder', 'research-worker-early',
            '--state', 'completed', '--item', 'C-001/R1', '--summary', 'Done.',
            '--evidence', 'commit abc', ok=False))

    def test_advanced_report_survives_another_worker_reclaiming_the_item(self):
        first = self.claim(holder='research-worker-first')
        self.cmd('finish', '--token', first, '--state', 'ready',
                 '--note', 'Continue from the recorded baseline.')
        self.claim(holder='research-worker-second')
        result = self.cmd(
            'report', '--worker', 'research-worker', '--holder', 'research-worker-first',
            '--state', 'advanced', '--item', 'C-001/R1', '--summary', 'Baseline recorded.',
            '--continuation', 'Continue from the recorded baseline.')
        self.assertEqual(result['entry']['state'], 'advanced')

    def test_reports_since_reads_late_entries_across_daily_files(self):
        sink = self.portfolio / '.briefing/daily'
        sink.mkdir(parents=True)
        old = datetime.now(timezone.utc) - timedelta(days=2)
        late = datetime.now(timezone.utc) - timedelta(hours=1)
        for timestamp, run_id, filename in (
            (old, 'old-run', 'old.md'),
            (late, 'late-run', 'late.md'),
        ):
            payload = {
                'version': 1, 'timestamp': timestamp.isoformat(),
                'worker': 'research-worker', 'run_id': run_id,
                'state': 'no-op', 'item': None, 'summary': run_id,
                'evidence': [], 'continuation': None,
            }
            (sink / filename).write_text(
                f"# Worker close-outs\n\n<!-- worker-closeout: {json.dumps(payload)} -->\n")
        since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        reports = self.cmd('reports', '--since', since)['reports']
        self.assertEqual([entry['run_id'] for entry in reports], ['late-run'])
        self.assertIn('timezone offset', self.cmd(
            'reports', '--since', '2026-09-16T12:20:00', ok=False))

    def test_brief_window_replays_after_failed_delivery_and_advances_after_success(self):
        sink = self.portfolio / '.briefing/daily'
        sink.mkdir(parents=True)
        base = datetime.now(timezone.utc) - timedelta(hours=3)
        for hours, run_id in ((0, 'first'), (1, 'second'), (2, 'third')):
            timestamp = base + timedelta(hours=hours)
            payload = {
                'version': 1, 'timestamp': timestamp.isoformat(),
                'worker': 'research-worker', 'run_id': run_id,
                'state': 'no-op', 'item': None, 'summary': run_id,
                'evidence': [], 'continuation': None,
            }
            (sink / f'{run_id}.md').write_text(
                f"<!-- worker-closeout: {json.dumps(payload)} -->\n")
        first = self.cmd('brief-window', '--previous-delivery', 'unknown',
                         '--through', (base + timedelta(minutes=30)).isoformat())
        self.assertEqual([entry['run_id'] for entry in first['reports']], ['first'])
        replay = self.cmd('brief-window', '--previous-delivery', 'failed',
                          '--through', (base + timedelta(hours=1, minutes=30)).isoformat())
        self.assertEqual([entry['run_id'] for entry in replay['reports']], ['first', 'second'])
        advanced = self.cmd('brief-window', '--previous-delivery', 'success',
                            '--through', (base + timedelta(hours=2, minutes=30)).isoformat())
        self.assertEqual([entry['run_id'] for entry in advanced['reports']], ['third'])


if __name__ == '__main__':
    unittest.main()
