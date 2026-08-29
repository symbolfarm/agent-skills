#!/usr/bin/env python3
"""Reject staged text containing private-boundary denylist terms.

Add checkout-specific terms one per line to
`.git/info/public-boundary-denylist`; that file is local Git metadata and can
therefore name private projects or people without publishing the denylist.
`PUBLIC_BOUNDARY_DENYLIST` may also point to an external newline-delimited file.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

# These markers catch explicitly labelled private paste blocks everywhere. They
# are assembled so this source file does not reject itself.
BASELINE = (
    "[" + "PRIVATE EXAMPLE]",
    "[" + "INTERNAL ONLY]",
    "BEGIN " + "PRIVATE",
)


def git_dir() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        check=True,
        capture_output=True,
        text=True,
    )
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
    # Preserve order for stable output while removing duplicates.
    return list(dict.fromkeys(terms))


def main(paths: list[str]) -> int:
    terms = denylist()
    violations: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(lines, start=1):
            folded = line.casefold()
            for term in terms:
                if term.casefold() in folded:
                    violations.append(f"{path}:{number}: denied term {term!r}")
    if not violations:
        return 0
    print("Public/private boundary check failed:", file=sys.stderr)
    for violation in violations:
        print(f"  {violation}", file=sys.stderr)
    print(
        "Move motivating examples to the private portfolio or edit the local "
        "denylist if this is a false positive.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
