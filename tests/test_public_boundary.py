from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check-public-boundary.py"


class PublicBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        self.git_run("git", "init", "-q")
        self.git_run("git", "config", "user.name", "Boundary Test")
        self.git_run("git", "config", "user.email", "boundary@example.invalid")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def git_run(
        self, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=self.repo,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    def check(
        self, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CHECKER), *args],
            cwd=self.repo,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    def local_denylist(self, term: str) -> None:
        path = self.repo / ".git" / "info" / "public-boundary-denylist"
        path.write_text(f"# checkout-private values\n{term}\n", encoding="utf-8")

    def test_staged_mode_reads_index_not_worktree(self) -> None:
        private_term = "Example Private Person"
        self.local_denylist(private_term)
        path = self.repo / "note.md"
        path.write_text(f"contact: {private_term}\n", encoding="utf-8")
        self.git_run("git", "add", "note.md")
        path.write_text("contact: <owner>\n", encoding="utf-8")

        staged = self.check("--staged")
        worktree = self.check("note.md")

        self.assertEqual(staged.returncode, 1)
        self.assertEqual(worktree.returncode, 0)
        self.assertIn("note.md:1: denied private term #", staged.stderr)
        self.assertNotIn(private_term, staged.stderr)

    def test_private_term_is_not_echoed_in_diagnostic(self) -> None:
        private_term = "Private Project Codename"
        self.local_denylist(private_term)
        path = self.repo / "reference.md"
        path.write_text(f"origin: {private_term}\n", encoding="utf-8")

        result = self.check("reference.md")

        self.assertEqual(result.returncode, 1)
        self.assertIn("reference.md:1: denied private term #", result.stderr)
        self.assertNotIn(private_term, result.stderr)

    def test_external_private_denylist_stays_external(self) -> None:
        private_term = "External Private Identifier"
        external = self.repo.parent / f"{self.repo.name}-denylist"
        external.write_text(f"{private_term}\n", encoding="utf-8")
        self.addCleanup(lambda: external.unlink(missing_ok=True))
        path = self.repo / "reference.md"
        path.write_text(f"origin: {private_term}\n", encoding="utf-8")
        env = dict(os.environ, PUBLIC_BOUNDARY_DENYLIST=str(external))

        result = self.check("reference.md", env=env)

        self.assertEqual(result.returncode, 1)
        self.assertNotIn(private_term, result.stderr)

    def test_staged_mode_ignores_deleted_and_untracked_files(self) -> None:
        self.local_denylist("Private Marker")
        tracked = self.repo / "tracked.md"
        tracked.write_text("safe\n", encoding="utf-8")
        self.git_run("git", "add", "tracked.md")
        self.git_run("git", "commit", "-qm", "seed")
        tracked.unlink()
        self.git_run("git", "add", "tracked.md")
        (self.repo / "untracked.md").write_text("Private Marker\n", encoding="utf-8")

        result = self.check("--staged")

        self.assertEqual(result.returncode, 0)

    def test_empty_index_passes(self) -> None:
        self.local_denylist("Private Marker")
        result = self.check("--staged")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_rename_and_copy_are_scanned_in_staged_mode(self) -> None:
        self.local_denylist("Private Marker")
        source = self.repo / "source.md"
        source.write_text("content\n", encoding="utf-8")
        self.git_run("git", "add", "source.md")
        self.git_run("git", "commit", "-qm", "seed")
        renamed = self.repo / "renamed.md"
        renamed.write_text("content Private Marker\n", encoding="utf-8")
        self.git_run("git", "add", "-A")

        result = self.check("--staged")

        self.assertEqual(result.returncode, 1)
        self.assertIn("renamed.md:1: denied private term #", result.stderr)
        self.assertNotIn("Private Marker", result.stderr)

    def test_baseline_marker_fires_without_local_denylist(self) -> None:
        path = self.repo / "note.md"
        # Build the marker from parts so this fixture source is not itself flagged.
        path.write_text("BEGIN " "PRIVATE\n", encoding="utf-8")

        result = self.check("note.md")

        self.assertEqual(result.returncode, 1)
        self.assertIn("note.md:1: denied private term #", result.stderr)

    def test_non_utf8_blob_is_skipped_in_staged_mode(self) -> None:
        self.local_denylist("Private Marker")
        path = self.repo / "data.bin"
        path.write_bytes(b"Private Marker" + b"\xff\xfe" + b"\x00")
        self.git_run("git", "add", "data.bin")

        result = self.check("--staged")

        self.assertEqual(result.returncode, 0)

    def test_no_args_is_fail_closed(self) -> None:
        result = self.check()
        self.assertEqual(result.returncode, 2)
        self.assertIn("nothing to scan", result.stderr)

    def test_outside_a_repository_is_fail_closed(self) -> None:
        # The temp repo's parent is an existing directory that is not a Git repo.
        outside = str(Path(self.tempdir.name).parent)
        result = subprocess.run(
            [sys.executable, str(CHECKER), "--staged"],
            cwd=outside,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("could not run", result.stderr)


if __name__ == "__main__":
    unittest.main()
