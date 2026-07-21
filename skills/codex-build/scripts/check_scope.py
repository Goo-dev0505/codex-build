#!/usr/bin/env python3
"""Fail when a task changes files outside its on-disk allowlist."""

from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare tracked and untracked worktree changes with an exact, "
            "newline-delimited file allowlist."
        )
    )
    parser.add_argument(
        "--allowlist",
        required=True,
        type=Path,
        help="file containing one repo-relative path per line",
    )
    parser.add_argument(
        "--repo",
        default=Path.cwd(),
        type=Path,
        help="target Git worktree (default: current directory)",
    )
    parser.add_argument(
        "--base",
        default="HEAD",
        help="Git revision to compare tracked changes against (default: HEAD)",
    )
    return parser.parse_args()


def load_allowlist(path: Path) -> set[str]:
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read allowlist {path}: {exc}") from exc

    allowed: set[str] = set()
    for line_number, raw_path in enumerate(raw_lines, start=1):
        if not raw_path:
            continue
        if raw_path != raw_path.strip():
            raise ValueError(
                f"allowlist line {line_number} has leading or trailing whitespace"
            )
        if "\\" in raw_path:
            raise ValueError(
                f"allowlist line {line_number} must use Git-style '/' separators"
            )

        path_parts = raw_path.split("/")
        candidate = PurePosixPath(raw_path)
        if (
            candidate.is_absolute()
            or raw_path.endswith("/")
            or any(part in {"", ".", ".."} for part in path_parts)
        ):
            raise ValueError(
                f"allowlist line {line_number} is not an exact repo-relative file: "
                f"{raw_path!r}"
            )
        allowed.add(candidate.as_posix())

    if not allowed:
        raise ValueError("allowlist contains no file paths")
    return allowed


def git_paths(repo: Path, *args: str) -> set[str]:
    command = ["git", "-C", os.fspath(repo), *args]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = os.fsdecode(result.stderr).strip()
        raise RuntimeError(f"{' '.join(command)} failed: {stderr}")
    return {
        os.fsdecode(raw_path)
        for raw_path in result.stdout.split(b"\0")
        if raw_path
    }


def changed_paths(repo: Path, base: str) -> set[str]:
    # --no-renames reports both sides of a rename, so both paths must be declared.
    tracked = git_paths(
        repo,
        "diff",
        "--name-only",
        "--no-renames",
        "-z",
        base,
        "--",
    )
    untracked = git_paths(
        repo,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
    )
    return tracked | untracked


def main() -> int:
    args = parse_args()
    try:
        allowed = load_allowlist(args.allowlist)
        changed = changed_paths(args.repo.resolve(), args.base)
    except (RuntimeError, ValueError) as exc:
        print(f"scope check error: {exc}", file=sys.stderr)
        return 2

    violations = sorted(changed - allowed)
    if violations:
        print(
            "scope check failed: changed paths outside the task allowlist:",
            file=sys.stderr,
        )
        for path in violations:
            print(f"  {path}", file=sys.stderr)
        return 1

    noun = "path" if len(changed) == 1 else "paths"
    print(f"scope check passed: {len(changed)} changed {noun} within the allowlist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
