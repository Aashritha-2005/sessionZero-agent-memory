"""One-off sanity check: confirm ingested memory units are queryable via recall()."""

from __future__ import annotations

import json

from ingest.remember_client import DATASET_NAME, _client


def main():
    with _client() as client:
        result = client.recall(
            query="Why was Redis pub/sub reverted for shift-change notifications?",
            datasets=[DATASET_NAME],
        )
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
