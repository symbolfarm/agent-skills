import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.repo_availability import check, first_available


NOW = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)


class RepoAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def make_repo(self, name, dirty=False, lock=None):
        repo = self.root / name
        (repo / ".tasks").mkdir(parents=True)
        (repo / "TASKS.md").write_text("# Tasks\n", encoding="utf-8")
        # LOCKING.md keeps the lock out of history; an un-ignored lock would
        # make every locked repository read as dirty as well.
        (repo / ".gitignore").write_text(".tasks/.lock\n", encoding="utf-8")
        for args in (
            ["init", "-q", "-b", "main"],
            ["config", "user.email", "fixture@example.invalid"],
            ["config", "user.name", "Fixture"],
            ["add", "-A"],
            ["commit", "-q", "-m", "initial"],
        ):
            subprocess.run(["git", "-C", str(repo)] + args, check=True, capture_output=True)
        if dirty:
            (repo / "residue.toml").write_text("someone_elses = true\n", encoding="utf-8")
        if lock is not None:
            (repo / ".tasks" / ".lock").write_text(lock, encoding="utf-8")
        return repo

    def lock_json(self, holder="hermes", expires=NOW + timedelta(hours=1)):
        return json.dumps(
            {
                "holder": holder,
                "item": "work-cycle G-999",
                "acquired_at": NOW.isoformat(),
                "expires_at": expires.isoformat(),
            }
        )

    # One dirty repository, one clean eligible item — the G-048 fixture.

    def test_one_dirty_repo_does_not_cost_the_clean_item(self):
        dirty = self.make_repo("blocked-repo", dirty=True)
        clean = self.make_repo("open-repo")

        selected, skipped = first_available(
            [("G-001", dirty), ("G-002", clean)], holder="claude", now=NOW
        )

        self.assertEqual(selected, ("G-002", clean))
        self.assertEqual([item_id for item_id, _ in skipped], ["G-001"])
        self.assertEqual(skipped[0][1].reason, "dirty")
        self.assertIn("residue.toml", skipped[0][1].detail)

    def test_dirty_repo_blocks_only_its_own_items(self):
        dirty = self.make_repo("blocked-repo", dirty=True)
        clean = self.make_repo("open-repo")

        selected, skipped = first_available(
            [("G-001", dirty), ("G-002", dirty), ("G-003", clean)], now=NOW
        )

        self.assertEqual(selected, ("G-003", clean))
        self.assertEqual([item_id for item_id, _ in skipped], ["G-001", "G-002"])

    def test_nothing_available_reports_every_skip(self):
        dirty = self.make_repo("blocked-repo", dirty=True)
        locked = self.make_repo("held-repo", lock=self.lock_json())

        selected, skipped = first_available([("G-001", dirty), ("G-002", locked)], now=NOW)

        self.assertIsNone(selected)
        self.assertEqual([state.reason for _, state in skipped], ["dirty", "locked"])

    def test_clean_unlocked_repo_is_available(self):
        state = check(self.make_repo("open-repo"), now=NOW)
        self.assertTrue(state.available)
        self.assertIsNone(state.reason)

    def test_live_lock_from_another_agent_blocks(self):
        state = check(self.make_repo("held-repo", lock=self.lock_json()), holder="claude", now=NOW)
        self.assertFalse(state.available)
        self.assertEqual(state.reason, "locked")
        self.assertIn("hermes", state.detail)

    def test_expired_lock_is_stale_and_available(self):
        repo = self.make_repo("held-repo", lock=self.lock_json(expires=NOW - timedelta(minutes=1)))
        state = check(repo, holder="claude", now=NOW)
        self.assertTrue(state.available)
        self.assertIn("stale lock", state.detail)

    def test_own_lock_does_not_block_its_holder(self):
        repo = self.make_repo("held-repo", lock=self.lock_json(holder="claude"))
        self.assertTrue(check(repo, holder="claude", now=NOW).available)
        self.assertFalse(check(repo, holder="hermes", now=NOW).available)

    def test_unreadable_lock_is_treated_as_held(self):
        state = check(self.make_repo("held-repo", lock="{not json"), now=NOW)
        self.assertFalse(state.available)
        self.assertEqual(state.reason, "locked")

    def test_lock_without_expiry_is_treated_as_held(self):
        state = check(self.make_repo("held-repo", lock=json.dumps({"holder": "hermes"})), now=NOW)
        self.assertFalse(state.available)
        self.assertEqual(state.reason, "locked")

    def test_non_repository_is_missing_not_available(self):
        (self.root / "not-a-repo").mkdir()
        state = check(self.root / "not-a-repo", now=NOW)
        self.assertFalse(state.available)
        self.assertEqual(state.reason, "missing")


if __name__ == "__main__":
    unittest.main()
