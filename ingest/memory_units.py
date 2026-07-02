"""Structures raw commits into discrete "memory units" for Cognee ingestion.

A memory unit is the atomic thing we hand to Cognee's remember(): one
architecture decision, one bug+fix pair, one rejected approach, etc. Each
carries the provenance (source commit hash + timestamp + files) that the
trust-scoring layer and dashboard provenance drill-down depend on later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from ingest.git_reader import Commit, read_commits

# Matches short git-style hashes (7 hex chars) *only when introduced by an
# explicit supersession phrase* — "reverts commit X", "Supersedes ... X",
# "changed from X" — so an incidental hash mention elsewhere in the prose
# (e.g. "not repeating the X mistake") isn't misread as a real reference.
_HASH_REF_RE = re.compile(
    r"(?:reverts commit|supersedes(?:[^.\n]*?(?:from|the))?|changed from)\s+"
    r"(?:the\s+)?(?:[a-z0-9_./-]*\s+)?(?:from\s+)?([0-9a-f]{7})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MemoryUnit:
    id: str  # stable id, derived from commit hash
    kind: str  # decision | bug_fix | revert | contradiction | deletion
    title: str  # first line of the commit message
    body: str  # full text handed to Cognee's remember()
    files: list[str]
    timestamp: datetime
    source_commit: str
    references: list[str] = field(default_factory=list)  # other commit hashes mentioned


def _extract_references(message: str, own_hash: str) -> list[str]:
    found = {h for h in _HASH_REF_RE.findall(message) if h != own_hash}
    return sorted(found)


def commit_to_memory_unit(commit: Commit) -> MemoryUnit:
    title = commit.message.splitlines()[0]
    body = (
        f"[{commit.type}] {commit.message}\n\n"
        f"Files touched: {', '.join(commit.files)}\n"
        f"Diff summary: {commit.diff_summary}\n"
        f"Commit: {commit.hash} ({commit.timestamp.isoformat()}) by {commit.author}"
    )
    return MemoryUnit(
        id=f"mu-{commit.hash}",
        kind=commit.type,
        title=title,
        body=body,
        files=list(commit.files),
        timestamp=commit.timestamp,
        source_commit=commit.hash,
        references=_extract_references(commit.message, commit.hash),
    )


def build_memory_units(commits: list[Commit] | None = None) -> list[MemoryUnit]:
    commits = commits if commits is not None else read_commits()
    return [commit_to_memory_unit(c) for c in commits]


if __name__ == "__main__":
    for unit in build_memory_units():
        refs = f" (refs: {', '.join(unit.references)})" if unit.references else ""
        print(f"{unit.id:>16}  {unit.kind:>13}  {unit.title}{refs}")
