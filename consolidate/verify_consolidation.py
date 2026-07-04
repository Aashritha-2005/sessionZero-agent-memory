"""Verification: does the reframed recall()+forget() consolidation
actually remove the superseded mu-a1f3c02 (local Docker Postgres)
memory from the graph, now that it's contradicted by mu-2c9e4f1
(Railway Postgres)? Captures real recall() output before and after."""

from __future__ import annotations

import json

from consolidate.memify_job import consolidate_contradictions
from ingest.remember_client import DATASET_NAME, _client

QUERY = "Is ShiftLog's Postgres running locally via Docker?"


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

    print("\n--- running real consolidate_contradictions() (forget on superseded commits) ---")
    result = consolidate_contradictions()
    print(json.dumps(result, indent=2, default=str))

    after = snapshot("AFTER forget()")

    before_commits = {
        next((line for line in c.get("text", "").splitlines() if line.startswith("Commit:")), None)
        for c in before
    }
    after_commits = {
        next((line for line in c.get("text", "").splitlines() if line.startswith("Commit:")), None)
        for c in after
    }
    removed = before_commits - after_commits
    print(f"\n=== DIFF: commits present before but gone after ===\n{removed}")


if __name__ == "__main__":
    main()
