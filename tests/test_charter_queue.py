import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/charter_queue.py'


class CharterQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.portfolio = self.root / 'portfolio'
        self.portfolio.mkdir()
        self.repo = self.make_repo('research')
        self.queue = self.portfolio / 'QUEUE.json'
        (self.portfolio / 'charter.md').write_text('# Question\n\n### R1 — Compare\n\n### R2 — Explain\n')
        self.data = {'version': 1, 'charters': [{
            'id': 'C-001', 'path': 'charter.md', 'status': 'active',
            'authorized_by': 'Fixture user, explicit test authorization', 'lane': 'research',
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

    def claim(self, holder='run-a'):
        return self.cmd('claim', '--holder', holder, '--lane', 'research',
                        '--capability', 'general')['selected']['requirement']['claim']['token']

    def test_empty_queue_never_discovers_legacy_work(self):
        self.data['charters'] = []
        self.write()
        (self.portfolio / 'GOALS.md').write_text('## Queue\n- **G-001** `research` — old work\n')
        self.assertIsNone(self.cmd('next')['selected'])

    def test_draft_deferral_capability_lane_and_dependency_gates(self):
        self.assertIsNone(self.cmd('next', '--lane', 'product', '--capability', 'general')['selected'])
        self.assertIsNone(self.cmd('next', '--lane', 'research')['selected'])
        self.data['charters'][0]['requirements'][0]['state'] = 'deferred'
        self.write()
        self.assertIsNone(self.cmd('next', '--capability', 'general')['selected'])
        self.data['charters'][0]['status'] = 'draft'
        self.data['charters'][0]['requirements'][0]['state'] = 'ready'
        self.write()
        self.assertIsNone(self.cmd('next', '--capability', 'general')['selected'])

    def test_done_needs_evidence_and_unlocks_dependents(self):
        token = self.claim()
        self.cmd('check-exit', '--holder', 'run-a', ok=False)
        self.cmd('finish', '--token', token, '--state', 'done', ok=False)
        self.assertTrue((self.repo / '.tasks/.lock').exists())
        self.cmd('finish', '--token', token, '--state', 'done', '--evidence', 'artifact: comparison established')
        self.assertFalse((self.repo / '.tasks/.lock').exists())
        self.cmd('check-exit', '--holder', 'run-a')
        self.assertEqual(self.cmd('next')['selected']['item'], 'C-001/R2')

    def test_dirty_completion_refused_and_continuation_preserves_work(self):
        token = self.claim()
        work = self.repo / 'result.txt'
        work.write_text('incomplete result')
        self.cmd('finish', '--token', token, '--state', 'done', '--evidence', 'result', ok=False)
        self.cmd('finish', '--token', token, '--state', 'ready', '--note', 'Finish comparison')
        self.assertEqual(work.read_text(), 'incomplete result')
        self.assertIsNone(self.cmd('next', '--capability', 'general')['selected'])
        self.cmd('check-exit', '--holder', 'run-a')

    def test_task_inherits_parent_and_cannot_escape_repository(self):
        token = self.claim()
        result = self.cmd('task', '--token', token, '--repo', str(self.repo), '--id', 'EXP-1', '--title', 'Compare')
        self.assertIn('Parent: C-001/R1', Path(result['task']).read_text())
        self.assertTrue(json.loads(self.queue.read_text())['charters'][0]['requirements'][0]['tasks'])
        self.cmd('task', '--token', token, '--repo', str(self.root), '--id', 'EXP-2', '--title', 'bad', ok=False)
        self.cmd('task', '--token', token, '--repo', str(self.repo), '--id', '../escape', '--title', 'bad', ok=False)

    def test_concurrent_claims_have_one_winner(self):
        argv = [sys.executable, str(SCRIPT), '--queue', str(self.queue), 'claim', '--capability', 'general', '--holder']
        ps = [subprocess.Popen([*argv, holder], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
              for holder in ['run-a', 'run-b']]
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
        self.cmd('check-exit', '--holder', 'run-a', ok=False)

    def test_dirty_repo_skips_to_clean_requirement(self):
        clean = self.make_repo('clean')
        (self.repo / 'residue').write_text('keep')
        self.data['charters'][0]['requirements'][1]['repos'] = ['../clean']
        self.data['charters'][0]['requirements'][1]['depends_on'] = []
        self.write()
        self.assertEqual(self.cmd('next', '--capability', 'general')['selected']['item'], 'C-001/R2')
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
        self.assertIsNone(self.cmd('claim', '--holder', 'run-a', '--capability', 'general')['selected'])
        self.assertFalse((clean / '.tasks/.lock').exists())

    def test_control_repository_must_be_clean_before_claim(self):
        (self.portfolio / '.gitignore').write_text('.charter-queue.lock\n.queue-*\n')
        for args in (['init', '-q'], ['config', 'user.email', 'test@example.invalid'],
                     ['config', 'user.name', 'Test'], ['add', '.'], ['commit', '-qm', 'queue']):
            subprocess.run(['git', '-C', str(self.portfolio), *args], check=True, capture_output=True)
        (self.portfolio / 'uncommitted.md').write_text('another author')
        self.cmd('claim', '--holder', 'run-a', '--capability', 'general', ok=False)
        self.assertFalse((self.repo / '.tasks/.lock').exists())

    def test_complete_handoff_lifecycle_with_real_commits(self):
        (self.portfolio / '.gitignore').write_text('.charter-queue.lock\n.queue-*\n')
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
        for args in (['add', 'QUEUE.json'], ['commit', '-qm', 'close']):
            subprocess.run(['git', '-C', str(self.portfolio), *args], check=True, capture_output=True)
        self.cmd('check-exit', '--holder', 'run-a')
        for repo in (self.repo, self.portfolio):
            status = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True)
            self.assertEqual(status, '')
        self.assertEqual(self.cmd('next')['selected']['item'], 'C-001/R2')

    def test_recovery_preserves_continuation_and_releases_own_locks(self):
        token = self.claim()
        self.cmd('recover', '--token', token, '--reason', 'Confirmed stopped; resume baseline')
        self.assertFalse((self.repo / '.tasks/.lock').exists())
        self.assertIn('resume baseline', self.cmd('next', '--capability', 'general')['selected']['requirement']['progress'])


if __name__ == '__main__':
    unittest.main()
