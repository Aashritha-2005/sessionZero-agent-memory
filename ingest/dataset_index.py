"""Resolves Cognee's real data_id for each ingested memory unit.

remember() doesn't return a stable 1:1 (memory_unit -> data_id) mapping
in its response (its "items" list is cumulative/chunk-level across
calls). To get real, addressable data_ids for forget(), we list the
dataset's data via GET /api/v1/datasets/{id}/data and fetch each item's
raw text via GET .../data/{data_id}/raw, then match the embedded
"Commit: <hash>" line the same way recall_service/trust_score.py does.
This is all real Cognee Cloud API traffic — no mocking.
"""

from __future__ import annotations

from recall_service.trust_score import extract_commit_hash


def get_dataset_id(client, dataset_name: str) -> str:
    resp = client._get_client().get(client._url("/api/v1/datasets/"))
    client._raise_for_status(resp)
    for d in resp.json():
        if d.get("name") == dataset_name:
            return d["id"]
    raise RuntimeError(f"Dataset '{dataset_name}' not found")


def build_commit_to_data_id(client, dataset_id: str) -> dict[str, str]:
    resp = client._get_client().get(client._url(f"/api/v1/datasets/{dataset_id}/data"))
    client._raise_for_status(resp)
    items = resp.json()

    mapping: dict[str, str] = {}
    for item in items:
        data_id = item["id"]
        raw_resp = client._get_client().get(
            client._url(f"/api/v1/datasets/{dataset_id}/data/{data_id}/raw")
        )
        client._raise_for_status(raw_resp)
        commit_hash = extract_commit_hash(raw_resp.text)
        if commit_hash:
            mapping[commit_hash] = data_id
    return mapping
