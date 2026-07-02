"""Verification: prune_deleted_files() should remove the mu-5f2b7c4
(legacy CSV export removal) memory from the graph. Real before/after
recall() snapshots, same pattern as consolidate/verify_consolidation.py."""

from __future__ import annotations

import json

from ingest.remember_client import DATASET_NAME, _client
from prune.forget_watcher import prune_deleted_files

QUERY = "Does ShiftLog have a CSV export feature?"


def snapshot(label: str) -> list[dict]:
    with _client() as client:
        chunks = client.recall(
            query=QUERY,
            search_type="CHUNKS",
            datasets=[DATASET_NAME],
            top_k=10,
        )
    print(f"\n=== SNAPSHOT [{label}] — {len(chunks)} chunk(s) ===")
    for c in chunks:
        commit_line = next(
            (line for line in c.get("text", "").splitlines() if line.startswith("Commit:")), None
        )
        print(f"  {commit_line}")
    return chunks


def main():
    before = snapshot("BEFORE forget()")

    print("\n--- running real prune_deleted_files() ---")
    from dataclasses import asdict

    log = prune_deleted_files()
    print(json.dumps([asdict(e) for e in log], indent=2, default=str))

    after = snapshot("AFTER forget()")

    before_commits = {
        next((l for l in c.get("text", "").splitlines() if l.startswith("Commit:")), None) for c in before
    }
    after_commits = {
        next((l for l in c.get("text", "").splitlines() if l.startswith("Commit:")), None) for c in after
    }
    removed = before_commits - after_commits
    print(f"\n=== DIFF: commits present before but gone after ===\n{removed}")


if __name__ == "__main__":
    main()
