"""Reads project commit history.

Source: demo-data/commits.jsonl inside this repo (synthetic but
realistic sample data — see demo-data/README.md for why). Named
git_reader.py because it stands in the same pipeline position a real
`git log --stat` / `git show` reader would occupy; swapping in a real
repo later only means replacing `read_commits()`'s implementation.
"""

from __future__ import annotations

import json
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


if __name__ == "__main__":
    for commit in read_commits():
        print(f"{commit.timestamp.date()} [{commit.type:>13}] {commit.hash}  {commit.message.splitlines()[0]}")
