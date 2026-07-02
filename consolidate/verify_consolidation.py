"""Verification: does real improve()/memify() actually change anything
about the mu-2c9e4f1 (Railway) vs mu-a1f3c02 (local Docker) contradiction
pair? Captures CHUNKS results before and after a real improve() call and
diffs the raw fields (feedback_weight, importance_weight, count, text)
so we can see genuine before/after effect, not just claim one."""

from __future__ import annotations

import json

from consolidate.memify_job import run_improve
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
        raw = c.get("raw", {}) or {}
        print(
            json.dumps(
                {
                    "commit_line": next(
                        (line for line in c.get("text", "").splitlines() if line.startswith("Commit:")),
                        None,
                    ),
                    "feedback_weight": raw.get("feedback_weight"),
                    "importance_weight": raw.get("importance_weight"),
                    "topological_rank": raw.get("topological_rank"),
                    "version": raw.get("version"),
                },
                indent=2,
            )
        )
    return chunks


def main():
    before = snapshot("BEFORE improve()")

    print("\n--- calling real improve() ---")
    result = run_improve()
    print(json.dumps(result, indent=2, default=str))

    after = snapshot("AFTER improve()")

    print(f"\n=== DIFF SUMMARY ===")
    print(f"chunks before: {len(before)}  chunks after: {len(after)}")


if __name__ == "__main__":
    main()
