#!/usr/bin/env python3
"""Reject public text containing checkout-private denylist terms.

The pre-commit mode reads blobs from Git's index, not mutable worktree files, so
partially staged changes cannot bypass the check. Add checkout-specific terms one
per line to `.git/info/public-boundary-denylist`; that file is local Git metadata
and is never committed. `PUBLIC_BOUNDARY_DENYLIST` may point to another local
newline-delimited file.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

# Catch explicitly labelled private paste blocks in every checkout. Assemble the
# strings so this source file does not reject itself.
BASELINE = (
    "[" + "PRIVATE EXAMPLE]",
    "[" + "INTERNAL ONLY]",
    "BEGIN " + "PRIVATE",
)


def run_git(*args: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=text,
    )


def git_dir() -> Path:
    result = run_git("rev-parse", "--git-dir")
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "not inside a Git repository")
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else Path.cwd() / path


def read_terms(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def denylist() -> list[str]:
    terms: list[str] = list(BASELINE)
    terms.extend(read_terms(git_dir() / "info" / "public-boundary-denylist"))
    external = os.environ.get("PUBLIC_BOUNDARY_DENYLIST")
    if external:
        terms.extend(read_terms(Path(external)))

    # Preserve stable diagnostic numbers while deduplicating case-insensitively.
    unique: dict[str, str] = {}
    for term in terms:
        unique.setdefault(term.casefold(), term)
    return list(unique.values())


def staged_paths() -> list[str]:
    result = run_git(
        "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z", text=False
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or "could not read the Git index")
    return [
        raw.decode("utf-8", errors="surrogateescape")
        for raw in result.stdout.split(b"\0")
        if raw
    ]


def read_worktree(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def read_staged(path: str) -> str | None:
    result = run_git("cat-file", "blob", f":{path}", text=False)
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or f"could not read staged blob {path!r}")
    try:
        return result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


def sanitize(text: str) -> str:
    """Neutralize control characters so a hostile filename cannot inject log lines."""
    return "".join(ch if ch.isprintable() or ch == "\t" else "?" for ch in text)


def check(paths: list[str], *, staged: bool) -> int:
    terms = denylist()
    violations: list[str] = []
    reader = read_staged if staged else read_worktree

    for path in paths:
        content = reader(path)
        if content is None:
            continue
        for number, line in enumerate(content.splitlines(), start=1):
            folded = line.casefold()
            for term_number, term in enumerate(terms, start=1):
                if term.casefold() in folded:
                    # Never echo a checkout-private term into terminal or CI logs.
                    violations.append(
                        f"{sanitize(path)}:{number}: denied private term #{term_number}"
                    )

    if not violations:
        return 0
    print("Public/private boundary check failed:", file=sys.stderr)
    for violation in violations:
        print(f"  {violation}", file=sys.stderr)
    print(
        "Move the motivating example to private documentation, or inspect the "
        "checkout-local denylist if this is a false positive.",
        file=sys.stderr,
    )
    return 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--staged",
        action="store_true",
        help="scan added/modified/renamed blobs exactly as staged in Git",
    )
    parser.add_argument("paths", nargs="*", help="worktree files to scan")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if not args.staged and not args.paths:
        print(
            "Public/private boundary check: nothing to scan — pass --staged "
            "or file arguments.",
            file=sys.stderr,
        )
        return 2
    try:
        paths = staged_paths() if args.staged else args.paths
        return check(paths, staged=args.staged)
    except RuntimeError as error:
        print(f"Public/private boundary check could not run: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
