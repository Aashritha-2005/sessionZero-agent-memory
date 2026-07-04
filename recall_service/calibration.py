"""Small-sample, directional calibration check for trust_score.py.

HONESTY NOTE (read before trusting this): this is explicitly NOT "real
statistical calibration with a proper labeled validation set" — that
requires an independent, non-leaky ground-truth process and far more
data than 15 memory units can provide to be statistically meaningful.
This script does not claim otherwise. It's a small, directional sanity
check: does the score ordering broadly track a real (if small) ground
truth signal, using data we already have? Report the actual numbers,
whatever they are, with the sample size stated plainly next to every
result — never implied to generalize beyond this dataset.

GROUND TRUTH (real, not fabricated): a memory unit is "valid" iff it's
neither forgotten (absent from the live Cognee dataset, checked via
ingest/dataset_index.py) nor superseded (its commit hash is a key in
recall_service.trust_score.build_contradiction_index()). Both signals
already drive real forget()/dashboard decisions elsewhere in this repo.

QUERY SET: each memory unit's own commit-message title, used as the
recall() query — a natural, non-cherry-picked proxy for "someone asks
about this topic."

SAMPLE UNIT: every (query, returned_memory) pair from a real CHUNKS
recall() call, scored via the real trust_score.score_chunks().
"""

from __future__ import annotations

import json

from ingest.dataset_index import build_commit_to_data_id, get_dataset_id
from ingest.memory_units import build_memory_units
from ingest.remember_client import DATASET_NAME, _client
from recall_service.trust_score import build_contradiction_index, score_chunks


def build_ground_truth(dataset_name: str = DATASET_NAME) -> dict[str, bool]:
    """commit_hash -> True (valid/current) / False (stale: forgotten or superseded)."""
    units = build_memory_units()
    contradiction_index = build_contradiction_index(units)

    with _client() as client:
        client.health()
        dataset_id = get_dataset_id(client, dataset_name)
        commit_to_data_id = build_commit_to_data_id(client, dataset_id)

    ground_truth = {}
    for unit in units:
        forgotten = unit.source_commit not in commit_to_data_id
        superseded = unit.source_commit in contradiction_index
        ground_truth[unit.source_commit] = not (forgotten or superseded)
    return ground_truth


def collect_samples(dataset_name: str = DATASET_NAME, top_k: int = 15) -> list[dict]:
    units = build_memory_units()
    ground_truth = build_ground_truth(dataset_name)

    samples = []
    with _client() as client:
        client.health()
        for i, unit in enumerate(units):
            chunks = client.recall(
                query=unit.title,
                search_type="CHUNKS",
                datasets=[dataset_name],
                top_k=top_k,
            )
            results = score_chunks(chunks, top_k=top_k)
            for r in results:
                if r.source_commit not in ground_truth:
                    continue  # e.g. references to un-ingested commits — skip, no ground truth
                samples.append(
                    {
                        "query_commit": unit.source_commit,
                        "result_commit": r.source_commit,
                        "score": r.score,
                        "label": r.label,
                        "ground_truth_valid": ground_truth[r.source_commit],
                    }
                )
            print(f"[{i+1}/{len(units)}] queried '{unit.title[:50]}' -> {len(results)} scored results")
    return samples


BUCKETS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]


def bucket_accuracy(samples: list[dict]) -> list[dict]:
    report = []
    for lo, hi in BUCKETS:
        bucketed = [s for s in samples if lo <= s["score"] < hi]
        n = len(bucketed)
        n_correct = sum(1 for s in bucketed if s["ground_truth_valid"])
        accuracy = (n_correct / n) if n else None
        report.append(
            {
                "bucket": f"[{lo:.1f}, {min(hi,1.0):.1f})",
                "n_samples": n,
                "n_ground_truth_valid": n_correct,
                "empirical_accuracy": round(accuracy, 3) if accuracy is not None else None,
            }
        )
    return report


if __name__ == "__main__":
    print("=== NOT statistically meaningful — small-sample directional check only ===\n")

    ground_truth = build_ground_truth()
    print("=== GROUND TRUTH (real, from live dataset state) ===")
    for commit, valid in ground_truth.items():
        print(f"  {commit}: {'VALID' if valid else 'STALE'}")
    n_valid = sum(ground_truth.values())
    print(f"Total: {len(ground_truth)} units, {n_valid} valid, {len(ground_truth) - n_valid} stale")

    print("\n=== COLLECTING SAMPLES (real recall() per memory unit) ===")
    samples = collect_samples()
    print(f"\nTotal samples: {len(samples)}")

    print("\n=== BUCKET ACCURACY (real numbers, small sample) ===")
    report = bucket_accuracy(samples)
    for row in report:
        print(json.dumps(row))

    with open("/tmp/calibration_samples.json", "w") as f:
        json.dump({"ground_truth": ground_truth, "samples": samples, "bucket_report": report}, f, indent=2)
    print("\nRaw samples saved to /tmp/calibration_samples.json")
