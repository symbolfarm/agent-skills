import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/charter_queue.py'
WORKERS_SCHEMA = Path(__file__).resolve().parents[1] / (
    'skills/charter-cycle/assets/workers.schema.json')


class QueueFixture(unittest.TestCase):
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


class CharterQueueTests(QueueFixture):

    def test_exhausted_active_charter_is_reported_not_closed(self):
        # Closing is a joint review decision; the helper only makes it visible.
        for req in self.data['charters'][0]['requirements']:
            req.update(state='dropped')
        self.write()
        self.assertEqual(self.cmd('validate')['awaiting_close'], ['C-001'])
        result = self.cmd('next', '--worker', 'research-worker')
        self.assertIsNone(result['selected'])
        self.assertEqual(result['awaiting_close'], ['C-001'])
        self.assertEqual(json.loads(self.queue.read_text())['charters'][0]['status'], 'active')

    def test_empty_queue_never_discovers_legacy_work(self):
        self.data['charters'] = []
        self.write()
        (self.portfolio / 'GOALS.md').write_text('## Queue\n- **G-001** `research` — old work\n')
        self.assertIsNone(self.cmd('next', '--worker', 'research-worker')['selected'])

    def test_legacy_holder_prefix_validates_history_but_not_new_claims(self):
        workers = json.loads(self.workers.read_text())
        workers['workers'][0]['legacy_holder_prefixes'] = ['old-research-worker']
        self.workers.write_text(json.dumps(workers))
        req = self.data['charters'][0]['requirements'][0]
        req.update(
            state='done',
            evidence='historical artifact',
            transitions=[{
                'holder': 'old-research-worker-run-a',
                'state': 'done',
                'at': '2026-09-01T09:00:00+09:30',
            }],
        )
        self.write()
        result = json.loads(json.dumps(self.cmd('validate')))
        self.assertTrue(result['valid'])
        self.cmd(
            'claim', '--worker', 'research-worker',
            '--holder', 'old-research-worker-run-b', ok=False)

    def test_current_and_legacy_holder_prefixes_must_be_globally_unique(self):
        original = json.loads(self.workers.read_text())
        for legacy_owner, current_owner in [(0, 1), (1, 0)]:
            with self.subTest(legacy_owner=legacy_owner):
                workers = json.loads(json.dumps(original))
                collision = workers['workers'][current_owner]['holder_prefix']
                workers['workers'][legacy_owner]['legacy_holder_prefixes'] = [collision]
                self.workers.write_text(json.dumps(workers))
                self.cmd('validate', ok=False)

    def test_worker_health_sources_must_be_independent(self):
        original = json.loads(self.workers.read_text())
        duplicates = [
            {'kind': 'hermes-cron', 'job_id': 'shared-job'},
            {'kind': 'file', 'path': '.briefing/health/shared.json'},
        ]
        for health in duplicates:
            with self.subTest(kind=health['kind']):
                workers = json.loads(json.dumps(original))
                for worker in workers['workers']:
                    worker['health'] = json.loads(json.dumps(health))
                self.workers.write_text(json.dumps(workers))
                self.cmd('validate', ok=False)
        workers = json.loads(json.dumps(original))
        workers['workers'][0]['health'] = {
            'kind': 'file', 'path': '.briefing/health/shared.json'}
        workers['workers'][1]['health'] = {
            'kind': 'file', 'path': '.briefing/health/../health/shared.json'}
        self.workers.write_text(json.dumps(workers))
        self.cmd('validate', ok=False)

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

    def git_portfolio(self):
        (self.portfolio / '.gitignore').write_text(
            '.charter-queue.lock\n.queue-*\n.briefing/\n')
        for args in (['init', '-q'], ['config', 'user.email', 'test@example.invalid'],
                     ['config', 'user.name', 'Test'], ['add', '.'], ['commit', '-qm', 'queue']):
            subprocess.run(['git', '-C', str(self.portfolio), *args], check=True, capture_output=True)

    def portfolio_status(self):
        return subprocess.check_output(
            ['git', '-C', str(self.portfolio), 'status', '--porcelain'], text=True)

    def test_uncommitted_queue_edit_blocks_a_claim(self):
        self.git_portfolio()
        self.data['charters'][0]['requirements'][0]['progress'] = 'hand edit in progress'
        self.write()
        self.cmd('claim', '--worker', 'research-worker', '--holder',
                 'research-worker-run-a', ok=False)
        self.assertFalse((self.repo / '.tasks/.lock').exists())

    def test_queue_commits_are_limited_to_the_queue_file(self):
        # Another worker's portfolio edits, staged or not, stay out of the
        # helper's commits and stay in the worktree untouched.
        self.git_portfolio()
        (self.portfolio / 'staged.md').write_text('another worker, staged')
        subprocess.run(['git', '-C', str(self.portfolio), 'add', 'staged.md'],
                       check=True, capture_output=True)
        (self.portfolio / 'loose.md').write_text('another worker, untracked')
        result = self.cmd('claim', '--worker', 'research-worker', '--holder', 'research-worker-run-a')
        self.assertIsNotNone(result['commit'])
        committed = subprocess.check_output(
            ['git', '-C', str(self.portfolio), 'show', '--name-only', '--format=%s', 'HEAD'],
            text=True).split()
        self.assertEqual(committed[-1], 'QUEUE.json')
        self.assertIn('C-001/R1: claim by research-worker-run-a', ' '.join(committed))
        self.assertEqual(sorted(self.portfolio_status().splitlines()),
                         ['?? loose.md', 'A  staged.md'])

    def test_workers_hold_separate_claims_concurrently(self):
        other = self.make_repo('product')
        (self.portfolio / 'product.md').write_text('### R1 — Ship\n')
        self.data['charters'].append({
            'id': 'P-001', 'path': 'product.md', 'status': 'active',
            'authorized_by': 'Fixture user, explicit test authorization',
            'eligible_workers': ['product-worker'],
            'requirements': [{'id': 'R1', 'state': 'ready', 'repos': ['../product']}]})
        self.write()
        self.git_portfolio()
        self.claim()
        second = self.cmd('claim', '--worker', 'product-worker', '--holder', 'product-worker-run-a')
        self.assertEqual(second['selected']['item'], 'P-001/R1')
        self.assertEqual(second['skipped'][0]['reason'], "another worker's active claim")
        self.assertEqual(second['skipped'][0]['items'][0]['item'], 'C-001/R1')
        self.assertTrue((other / '.tasks/.lock').exists())
        self.assertEqual(self.portfolio_status(), '')

    def test_another_workers_claim_still_blocks_its_repository(self):
        self.data['charters'][0]['eligible_workers'].append('product-worker')
        self.data['charters'][0]['requirements'][1]['depends_on'] = []
        self.write()
        self.claim()
        result = self.cmd('next', '--worker', 'product-worker')
        self.assertIsNone(result['selected'])
        self.assertIn({'item': 'C-001/R2', 'reason': f'repository lock present: {self.repo}'},
                      result['skipped'])

    def test_complete_handoff_lifecycle_with_real_commits(self):
        self.git_portfolio()
        token = self.claim()
        self.assertEqual(self.portfolio_status(), '')
        self.cmd('task', '--token', token, '--repo', str(self.repo), '--id', 'EXP-1', '--title', 'Compare')
        (self.repo / 'evidence.txt').write_text('baseline 0; intervention 1; fixture only')
        for args in (['add', '.'], ['commit', '-qm', 'comparison']):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True)
        self.cmd('finish', '--token', token, '--state', 'done', '--evidence', 'research/evidence.txt: fixture comparison')
        log = subprocess.check_output(['git', '-C', str(self.portfolio), 'log', '--format=%s'], text=True)
        self.assertIn('C-001/R1: done by research-worker-run-a', log)
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

    def test_transitions_must_name_a_configured_worker(self):
        token = self.claim()
        self.cmd('finish', '--token', token, '--state', 'ready', '--note', 'Continue.')
        self.assertEqual(self.cmd('validate')['charters'], 1)
        data = json.loads(self.queue.read_text())
        data['charters'][0]['requirements'][0]['transitions'].append(
            {'holder': 'unconfigured-seed', 'state': 'done',
             'at': '2026-01-01T00:00:00+00:00'})
        self.queue.write_text(json.dumps(data))
        self.assertIn('not a known worker', self.cmd('validate', ok=False))

    def test_brief_window_floor_bounds_a_never_confirmed_cursor(self):
        sink = self.portfolio / '.briefing/daily'
        sink.mkdir(parents=True)
        now = datetime.now(timezone.utc)
        for delta, run_id in ((timedelta(days=30), 'ancient'), (timedelta(hours=1), 'recent')):
            payload = {
                'version': 1, 'timestamp': (now - delta).isoformat(),
                'worker': 'research-worker', 'run_id': run_id,
                'state': 'no-op', 'item': None, 'summary': run_id,
                'evidence': [], 'continuation': None,
            }
            (sink / f'{run_id}.md').write_text(
                f"<!-- worker-closeout: {json.dumps(payload)} -->\n")
        window = self.cmd(
            'brief-window', '--previous-delivery', 'failed',
            '--through', now.isoformat(),
            '--earliest', (now - timedelta(days=1)).isoformat())
        self.assertEqual([entry['run_id'] for entry in window['reports']], ['recent'])

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


class DetachedJobTests(QueueFixture):
    """Jobs that outlive the agent session, metered against the charter budget."""

    def setUp(self):
        super().setUp()
        workers = json.loads(self.workers.read_text())
        workers['workers'][0]['max_job_hours'] = 1
        self.workers.write_text(json.dumps(workers))
        self.data['charters'][0]['gpu_hours'] = 2
        self.write()
        self.env = {**os.environ, 'CHARTER_JOB_POLL': '0.1', 'CHARTER_JOB_GRACE': '1',
                    'CHARTER_JOB_STALE': '3', 'AGENT_RUN_ID': 'run-1'}

    def cmd(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(SCRIPT), '--queue', str(self.queue), *args],
                           text=True, capture_output=True, env=self.env)
        self.assertEqual(r.returncode == 0, ok, r.stdout + r.stderr)
        return json.loads(r.stdout) if ok else r.stderr

    def start(self, token, hours, *command, ok=True):
        return self.cmd('job-start', '--token', token, '--hours', str(hours),
                        '--log', 'logs/job.log', '--', *command, ok=ok)

    def req(self):
        return json.loads(self.queue.read_text())['charters'][0]['requirements'][0]

    def test_job_outlives_the_session_and_the_next_run_resumes_it(self):
        token = self.claim()
        started = self.start(token, 0.5, 'sh', '-c', 'echo measured; sleep 1')
        self.assertAlmostEqual(started['gpu_hours_left'], 1.5)
        # The session can close out and exit with the claim deliberately held.
        self.cmd('check-exit', '--holder', 'research-worker-run-a')
        self.cmd('report', '--worker', 'research-worker', '--holder', 'research-worker-run-a',
                 '--state', 'advanced', '--item', 'C-001/R1', '--summary', 'Job started.',
                 '--continuation', 'Analyse logs/job.log.')
        self.assertEqual(self.cmd('jobs', '--wait', '--run', 'run-1')['running'], 0)
        self.assertEqual(self.cmd('next', '--worker', 'research-worker')['selected']['item'],
                         'C-001/R1')
        resumed = self.cmd('claim', '--worker', 'research-worker', '--holder', 'research-worker-run-b')
        self.assertEqual(resumed['resumed_from'], 'research-worker-run-a')
        new_token = resumed['selected']['requirement']['claim']['token']
        lock = json.loads((self.repo / '.tasks/.lock').read_text())
        self.assertEqual(lock['token'], new_token)
        job = self.req()['jobs'][0]
        self.assertEqual((job['status'], job['exit_code']), ('exited', 0))
        self.assertLess(job['hours_used'], 0.01)
        self.assertEqual(self.req()['transitions'][-1]['state'], 'handover')
        self.assertIn('measured', (self.repo / 'logs/job.log').read_text())
        (self.repo / '.gitignore').write_text('.tasks/.lock\nlogs/\n')
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-qam', 'ignore logs'],
                       check=True, capture_output=True)
        self.cmd('finish', '--token', new_token, '--state', 'done', '--evidence', 'logs/job.log: measured')
        self.assertFalse((self.repo / '.tasks/.lock').exists())

    def test_budget_and_profile_bound_every_job(self):
        token = self.claim()
        self.assertIn('max_job_hours', self.start(token, 1.5, 'true', ok=False))
        # Running jobs hold their whole reservation; finished ones are charged
        # what they used.
        self.start(token, 1, 'sleep', '2')
        self.start(token, 0.75, 'sleep', '2')
        self.assertIn('GPU-hours left', self.start(token, 0.5, 'true', ok=False))
        self.cmd('jobs', '--wait', '--run', 'run-1')
        self.start(token, 0.5, 'true')
        self.cmd('jobs', '--wait', '--run', 'run-1')

    def test_charter_without_a_budget_cannot_start_a_job(self):
        del self.data['charters'][0]['gpu_hours']
        self.write()
        self.assertIn('no gpu_hours budget', self.start(self.claim(), 0.1, 'true', ok=False))

    def test_job_is_stopped_at_its_deadline(self):
        token = self.claim()
        self.start(token, 1 / 3600, 'sleep', '30')
        self.cmd('jobs', '--wait', '--run', 'run-1')
        self.claim('research-worker-run-b')
        job = self.req()['jobs'][0]
        self.assertEqual(job['status'], 'killed-budget')
        self.assertLess(job['hours_used'], 5 / 3600)

    def test_running_job_blocks_resume_and_transitions(self):
        token = self.claim()
        self.start(token, 0.5, 'sleep', '3')
        blocked = self.cmd('next', '--worker', 'research-worker')
        self.assertIsNone(blocked['selected'])
        self.assertEqual(blocked['skipped'][0]['reason'], 'own detached job still running')
        self.assertIn('still running', self.cmd(
            'finish', '--token', token, '--state', 'ready', '--note', 'x', ok=False))
        self.cmd('jobs', '--wait', '--run', 'run-1')

    def test_lost_job_is_charged_to_its_last_heartbeat(self):
        token = self.claim()
        job_id = self.start(token, 0.5, 'sleep', '30')['job']['id']
        live_path = self.portfolio / '.jobs' / f'{job_id}.json'
        for _ in range(50):
            live = json.loads(live_path.read_text())
            if live.get('pid'):
                break
            time.sleep(0.1)
        # The container vanished: runner and job gone, heartbeat frozen.
        import signal as sig
        os.killpg(live['pid'], sig.SIGKILL)
        subprocess.run(['pkill', '-KILL', '-f', f'job-run {job_id}'], capture_output=True)
        time.sleep(0.3)
        live = json.loads(live_path.read_text())
        live['heartbeat'] = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        live_path.write_text(json.dumps(live))
        self.claim('research-worker-run-b')
        job = self.req()['jobs'][0]
        self.assertEqual(job['status'], 'lost')
        self.assertGreaterEqual(job['hours_used'], 0)


if __name__ == '__main__':
    unittest.main()
