"""Scheduled consolidation pass: intended to call Cognee's real
improve()/memify() to merge duplicate/contradictory memories and
reweight nodes based on retrieval usage.

KNOWN PLATFORM LIMITATION (verified 2026-07-02, not a bug in this code):
this project's Cognee Cloud tenant serves REST API v1.0.0, whose real
OpenAPI spec (GET /openapi.json) does not expose `/api/v1/improve` or
`/api/v1/memify` — only add/add_text/cognify/remember/recall/forget are
hosted. The pip-installed `cognee==1.2.2` SDK has `improve`/`memify` as
in-process Python functions, but those build a *separate local* graph
(via local `cognee.remember()`, which needs its own LLM key) — not the
`shiftlog_demo` dataset already ingested to the cloud tenant. Calling
them would not demonstrate consolidation on our real data.

Per user decision (2026-07-02): documenting this as a known limitation
rather than faking a call or building a disconnected local demo. This
function is left in place, ready to be pointed at a real endpoint the
moment the tenant exposes one — see `run_improve()` below, which will
raise clearly (not silently mock) if called against a tenant that
still 404s.
"""

from __future__ import annotations

from ingest.remember_client import DATASET_NAME, _client


def run_improve(dataset_name: str = DATASET_NAME) -> dict:
    """Call the real improve() endpoint. Will raise RuntimeError (API 404)
    on tenants that don't host it yet — see module docstring."""
    with _client() as client:
        client.health()
        result = client.improve(dataset_name=dataset_name)
    print(f"improve() on dataset '{dataset_name}' -> {result}")
    return result


if __name__ == "__main__":
    import json

    out = run_improve()
    print(json.dumps(out, indent=2, default=str))
