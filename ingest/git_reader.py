"""Reads project commit history.

Two sources, same output shape (list[Commit]):

1. **`read_commits()`** (default, unchanged) — demo-data/commits.jsonl
   inside this repo (synthetic but realistic sample data — see
   demo-data/README.md for why).

2. **`read_commits_from_repo()`** (new, additive) — a real repo's actual
   `git log` output, parsed via subprocess. Proves the pipeline isn't
   hardcoded to our synthetic fixture format. Real repos don't carry our
   `type` field (decision/bug_fix/revert/contradiction/deletion), so
   `_classify_message()` applies a conservative heuristic and falls back
   to a generic `"commit"` kind rather than guessing "decision" for
   everything — see its docstring for exactly what it can and can't detect.

Nothing about `read_commits()`'s existing behavior or default changed.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEMO_DATA_DIR = Path(__file__).resolve().parent.parent / "demo-data"
COMMITS_FILE = DEMO_DATA_DIR / "commits.jsonl"


@dataclass(frozen=True)
class Commit:
    hash: str
    timestamp: datetime
    author: str
    type: str  # decision | bug_fix | revert | contradiction | deletion
    message: str
    files: list[str]
    diff_summary: str


def read_commits(commits_file: Path = COMMITS_FILE) -> list[Commit]:
    """Load and parse the commit log, oldest first."""
    if not commits_file.exists():
        raise FileNotFoundError(
            f"No commit data at {commits_file}. Expected demo-data/commits.jsonl "
            "(see demo-data/README.md)."
        )

    commits: list[Commit] = []
    with commits_file.open() as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Bad JSON on line {line_no} of {commits_file}: {e}") from e

            commits.append(
                Commit(
                    hash=raw["hash"],
                    timestamp=datetime.fromisoformat(raw["timestamp"].replace("Z", "+00:00")),
                    author=raw["author"],
                    type=raw["type"],
                    message=raw["message"],
                    files=raw["files"],
                    diff_summary=raw["diff_summary"],
                )
            )

    commits.sort(key=lambda c: c.timestamp)
    return commits


# -- real-repo mode (additive, does not affect read_commits() above) --------

_RECORD_SEP = "\x1e"
_FIELD_SEP = "\x1f"
_LOG_FORMAT = _FIELD_SEP.join(["%h", "%aI", "%an", "%B"]) + _RECORD_SEP


def _classify_message(message: str) -> str:
    """Heuristic classification for real-world commit messages, which
    don't carry our demo-data's explicit `type` field.

    Detects: `revert` (message starts with "Revert" or contains git's own
    "This reverts commit" marker) and `deletion`/`bug_fix` (first-line
    keyword match). Everything else — the large majority of real commits —
    falls back to the generic `"commit"` kind rather than being guessed as
    a "decision", since we have no real signal either way. This means
    contradiction-detection (which only looks at `revert`/`contradiction`
    kinds) will find real reverts in real repos, but won't find
    "decision A superseded decision B" relationships real repos don't
    label explicitly the way our synthetic demo-data does.
    """
    first_line = message.splitlines()[0].lower() if message else ""
    if first_line.startswith("revert") or "this reverts commit" in message.lower():
        return "revert"
    if any(k in first_line for k in ("remove ", "delete ", "drop ")):
        return "deletion"
    if any(k in first_line for k in ("fix ", "fix:", "fixes ", "bugfix")) or first_line.startswith("fix"):
        return "bug_fix"
    return "commit"


def _files_for_commit(repo_path: Path, commit_hash: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return [f for f in result.stdout.splitlines() if f]


def _diff_summary_for_commit(repo_path: Path, commit_hash: str) -> str:
    result = subprocess.run(
        ["git", "show", "--shortstat", "--format=", commit_hash],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""


def read_commits_from_repo(repo_path: Path, max_count: int = 30) -> list[Commit]:
    """Parse a real repo's actual `git log` output into Commit objects —
    same shape `read_commits()` produces from demo-data/commits.jsonl,
    so `ingest/memory_units.py` doesn't need to know or care which
    source it came from.

    `repo_path` must be a real, local git repository. `max_count` bounds
    how many recent commits are read (per-commit `git show`/`diff-tree`
    calls are not free on large histories).
    """
    repo_path = Path(repo_path).resolve()
    if not (repo_path / ".git").exists():
        raise ValueError(f"{repo_path} does not look like a git repository (no .git dir)")

    log_result = subprocess.run(
        ["git", "log", f"--max-count={max_count}", f"--pretty=format:{_LOG_FORMAT}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    commits: list[Commit] = []
    for record in log_result.stdout.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record.strip():
            continue
        commit_hash, iso_date, author, message = record.split(_FIELD_SEP, maxsplit=3)
        commits.append(
            Commit(
                hash=commit_hash,
                timestamp=datetime.fromisoformat(iso_date),
                author=author,
                type=_classify_message(message),
                message=message.strip(),
                files=_files_for_commit(repo_path, commit_hash),
                diff_summary=_diff_summary_for_commit(repo_path, commit_hash),
            )
        )

    commits.sort(key=lambda c: c.timestamp)
    return commits


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--repo":
        repo_arg = Path(sys.argv[2])
        count_arg = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        selected_commits = read_commits_from_repo(repo_arg, max_count=count_arg)
    else:
        selected_commits = read_commits()

    for commit in selected_commits:
        title = commit.message.splitlines()[0]
        print(f"{commit.timestamp.date()} [{commit.type:>13}] {commit.hash}  {title}")
