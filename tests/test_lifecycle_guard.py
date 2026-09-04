from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "skills" / "work-cycle" / "scripts" / "lifecycle_guard.py"
SPEC = importlib.util.spec_from_file_location("lifecycle_guard", MODULE_PATH)
assert SPEC and SPEC.loader
lifecycle_guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lifecycle_guard
SPEC.loader.exec_module(lifecycle_guard)


class LifecycleGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write_goals(self, text: str) -> Path:
        path = self.root / "GOALS.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_stale_detector_only_reports_old_unmatched_claim(self) -> None:
        path = self.write_goals(
            """# Goals
## Queue
- **G-001** `demo` — old and unmatched.
  *Claimed:* hermes, 2026-03-01T08:00:00+00:00
- **G-002** `demo` — fresh control.
  *Claimed:* hermes, 2026-03-01T09:55:00+00:00
## Completed
- **G-003** `demo` — matched close control.
  *Claimed:* hermes, 2026-03-01T08:00:00+00:00
  **Done 2026-03-01.**
"""
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = lifecycle_guard.stale_claims(
                path, 30, dt.datetime(2026, 3, 1, 10, 0, tzinfo=dt.timezone.utc)
            )
        self.assertEqual(1, result)
        self.assertIn("G-001", output.getvalue())
        self.assertNotIn("G-002", output.getvalue())
        self.assertNotIn("G-003", output.getvalue())

    def test_goal_exit_names_unresolved_claim(self) -> None:
        path = self.write_goals(
            """# Goals
## Queue
- **G-001** `demo` — unfinished.
  *Claimed:* hermes, 2026-03-01T08:00:00+00:00
"""
        )
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            result = lifecycle_guard.goal_exit(path, ["G-001"])
        self.assertEqual(1, result)
        self.assertIn("G-001", error.getvalue())
        self.assertIn("open claim", error.getvalue())

    def test_goal_exit_accepts_progress_and_terminal_sections(self) -> None:
        path = self.write_goals(
            """# Goals
## Queue
- **G-001** `demo` — resumable.
  *Claimed:* hermes, 2026-03-01T08:00:00+00:00
  *Progress:* landed the parser; next run adds the CLI.
## Completed
- **G-002** `demo` — done.
  **Done 2026-03-01.**
## Blocked
- **G-003** `demo` — waiting on owner.
"""
        )
        self.assertEqual(0, lifecycle_guard.goal_exit(path, ["G-001", "G-002", "G-003"]))

    def test_task_exit_rejects_in_progress_but_accepts_completed(self) -> None:
        path = self.root / "LOG.jsonl"
        path.write_text(
            "\n".join(
                json.dumps(record)
                for record in (
                    {"id": "T-1", "status": "in_progress"},
                    {"id": "T-2", "status": "completed"},
                )
            )
            + "\n",
            encoding="utf-8",
        )
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            self.assertEqual(1, lifecycle_guard.task_exit(path, ["T-1"]))
        self.assertIn("T-1", error.getvalue())
        self.assertEqual(0, lifecycle_guard.task_exit(path, ["T-2"]))


if __name__ == "__main__":
    unittest.main()
