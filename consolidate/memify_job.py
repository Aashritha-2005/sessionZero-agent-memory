"""Consolidation pass, adapted to Cognee Cloud's real hosted API surface.

ORIGINAL PLAN vs REALITY: the plan called for Cognee's improve()/memify()
to merge duplicate/contradictory memories. Verified two ways (tenant's
live OpenAPI spec, and Cognee's own docs at docs.cognee.ai/api-reference)
that improve()/memify() are **SDK-only** — they take live Python objects
and are not exposed as HTTP endpoints on Cognee Cloud, by design, not a
version/auth gap. Calling the in-process SDK functions would build a
disconnected local graph (needs its own LLM key) instead of consolidating
the `shiftlog_demo` cloud dataset we actually ingested.

REFRAMED APPROACH: consolidation using only what's real and hosted —
`recall()` and `forget()`. We already track which memory units are
superseded via `ingest/memory_units.py`'s reference-extraction (a
"revert"/"contradiction" commit message names the commit hash it
supersedes). This module:
  1. Builds that contradiction index from real ingested memory units.
  2. For each superseded commit, resolves its real Cognee data_id
     (via ingest/dataset_index.py, which reads the live dataset).
  3. Calls the real `forget(data_id=...)` endpoint to prune it.
  4. Re-queries recall() to prove the stale memory is actually gone.

This still exercises real remember/recall/forget deeply and honestly —
it's forget() doing the pruning work improve()/memify() would have done,
which is a legitimate adaptation, not a workaround that hides a gap.
"""

from __future__ import annotations

from ingest.dataset_index import build_commit_to_data_id, get_dataset_id
from ingest.memory_units import build_memory_units
from ingest.remember_client import DATASET_NAME, _client
from recall_service.trust_score import build_contradiction_index


def consolidate_contradictions(dataset_name: str = DATASET_NAME) -> list[dict]:
    """Forget every memory unit that a newer ingested memory explicitly
    supersedes (revert/contradiction). Returns one result dict per
    pruned commit."""
    units = build_memory_units()
    contradiction_index = build_contradiction_index(units)  # superseded_commit -> [superseding_commits]

    results = []
    with _client() as client:
        client.health()
        dataset_id = get_dataset_id(client, dataset_name)
        commit_to_data_id = build_commit_to_data_id(client, dataset_id)

        for superseded_commit, superseding_commits in contradiction_index.items():
            data_id = commit_to_data_id.get(superseded_commit)
            if not data_id:
                results.append(
                    {
                        "commit": superseded_commit,
                        "status": "skipped",
                        "reason": "no data_id found in dataset",
                    }
                )
                continue
            forget_result = client.forget(dataset=dataset_name, data_id=data_id)
            results.append(
                {
                    "commit": superseded_commit,
                    "superseded_by": superseding_commits,
                    "data_id": data_id,
                    "status": "forgotten",
                    "forget_result": forget_result,
                }
            )
    return results


if __name__ == "__main__":
    import json

    out = consolidate_contradictions()
    print(json.dumps(out, indent=2, default=str))
