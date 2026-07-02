"""Wraps Cognee Cloud's remember() to ingest memory units.

Each MemoryUnit becomes one remember() call against the real Cognee Cloud
tenant (via CogneeApiClient, the same HTTP client the `cognee` CLI uses in
--api-url mode), tagged with a dataset name so it can be recalled /
consolidated / pruned as a coherent set later. No mocking (see
PROJECT_PLAN.md §7) — this hits the tenant's real REST API with
COGNEE_API_KEY.
"""

from __future__ import annotations

import os

from cognee.cli.api_client import CogneeApiClient
from dotenv import load_dotenv

from ingest.memory_units import MemoryUnit, build_memory_units

load_dotenv()

DATASET_NAME = "shiftlog_demo"


def _client() -> CogneeApiClient:
    base_url = os.getenv("COGNEE_API_BASE_URL")
    api_key = os.getenv("COGNEE_API_KEY")
    if not base_url or not api_key:
        raise RuntimeError(
            "Missing COGNEE_API_BASE_URL / COGNEE_API_KEY. Copy .env.example to .env "
            "and fill in your Cognee Cloud tenant credentials, then re-run."
        )
    headers = {"X-Api-Key": api_key}
    tenant_id = os.getenv("COGNEE_TENANT_ID")
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id
    # Graph extraction on the server can take well over a minute per item;
    # the client default (120s) was too short and truncated real runs.
    return CogneeApiClient(base_url, headers=headers, timeout=600.0)


def remember_unit(client: CogneeApiClient, unit: MemoryUnit, dataset_name: str = DATASET_NAME) -> dict:
    result = client.remember(data_items=[unit.body], dataset_name=dataset_name)
    print(f"remembered {unit.id} ({unit.kind}) -> {result}")
    return {"memory_unit_id": unit.id, "kind": unit.kind, "result": result}


def remember_all(units: list[MemoryUnit] | None = None, dataset_name: str = DATASET_NAME) -> list[dict]:
    units = units if units is not None else build_memory_units()
    results = []
    with _client() as client:
        client.health()
        for unit in units:
            try:
                results.append(remember_unit(client, unit, dataset_name=dataset_name))
            except Exception as e:
                print(f"FAILED {unit.id} ({unit.kind}) -> {type(e).__name__}: {e}")
                results.append({"memory_unit_id": unit.id, "kind": unit.kind, "error": str(e)})
    return results


if __name__ == "__main__":
    import json

    out = remember_all()
    print("\n=== RAW RESULTS ===")
    print(json.dumps(out, indent=2, default=str))
    ok = sum(1 for r in out if "result" in r)
    print(f"\n{ok}/{len(out)} memory units remembered successfully.")
