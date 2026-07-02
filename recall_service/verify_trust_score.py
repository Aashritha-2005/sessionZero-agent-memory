"""Verification script: run real trust scoring against the two cases
called out in the plan — the mu-e8c4a71 revert and the mu-2c9e4f1 vs
mu-a1f3c02 contradiction — and print full signal breakdowns so the
scores can be eyeballed, not just asserted in a test."""

from __future__ import annotations

import json

from ingest.remember_client import DATASET_NAME, _client
from recall_service.trust_score import score_chunks


def run_query(label: str, query: str, top_k: int = 5):
    print(f"\n{'=' * 70}\nQUERY [{label}]: {query!r}\n{'=' * 70}")
    with _client() as client:
        chunks = client.recall(
            query=query,
            search_type="CHUNKS",
            datasets=[DATASET_NAME],
            top_k=top_k,
        )
    results = score_chunks(chunks, top_k=top_k)
    for r in results:
        print(f"\n--- commit {r.source_commit} ---")
        print(f"score: {r.score:.3f}  label: {r.label}")
        print(f"signals: {json.dumps(r.signals.__dict__, indent=2)}")
        print(f"text: {r.text[:160]}...")
    return results


def main():
    # Case 1: the revert (should score HIGH — no contradiction, on-topic, recent-ish)
    run_query(
        "revert case",
        "Why was Redis pub/sub reverted for shift-change notifications?",
    )

    # Case 2: the contradiction pair — the OLD local-Docker-Postgres memory
    # (mu-a1f3c02) should score visibly LOWER than a clean memory because
    # it's contradicted by mu-2c9e4f1 (Railway migration).
    run_query(
        "contradiction case",
        "Is ShiftLog's Postgres running locally via Docker?",
    )

    # Control: a clean, uncontradicted, on-topic memory for comparison —
    # the N+1 query bug fix, nothing supersedes it.
    run_query(
        "clean control case",
        "How was the N+1 query bug on the manager dashboard fixed?",
    )


if __name__ == "__main__":
    main()
