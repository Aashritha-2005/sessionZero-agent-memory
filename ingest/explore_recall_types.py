"""One-off exploration: what raw fields does recall() give us per search_type?
Used to design trust_score.py signals against real API shapes, not guesses."""
from __future__ import annotations

import json

from ingest.remember_client import DATASET_NAME, _client


def main():
    with _client() as client:
        for search_type in ["CHUNKS", "TRIPLET_COMPLETION", "GRAPH_COMPLETION"]:
            print(f"\n=== {search_type} ===")
            try:
                result = client.recall(
                    query="Postgres database setup",
                    search_type=search_type,
                    datasets=[DATASET_NAME],
                    top_k=5,
                )
                print(json.dumps(result, indent=2, default=str)[:4000])
            except Exception as e:
                print(f"ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
