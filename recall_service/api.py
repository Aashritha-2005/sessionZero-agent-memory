"""FastAPI wrapper exposing trust-scored recall over HTTP.

GET /recall?query=...&top_k=15 — real Cognee CHUNKS recall, trust-scored.
GET /health — passthrough to the real Cognee Cloud tenant's health check.

This is what claude_code_bridge/bridge.py calls before a coding task, and
what the dashboard calls to browse memories/provenance.
"""

from __future__ import annotations

from fastapi import FastAPI, Query

from ingest.remember_client import DATASET_NAME, _client
from recall_service.trust_score import TrustResult, score_chunks

app = FastAPI(title="cognee-agent-memory recall_service")


def _result_to_dict(r: TrustResult) -> dict:
    return {
        "source_commit": r.source_commit,
        "text": r.text,
        "score": round(r.score, 3),
        "label": r.label,
        "signals": r.signals.__dict__,
    }


@app.get("/health")
def health():
    with _client() as client:
        return client.health()


@app.get("/recall")
def recall(query: str = Query(...), top_k: int = Query(10, ge=1, le=50)):
    with _client() as client:
        chunks = client.recall(
            query=query,
            search_type="CHUNKS",
            datasets=[DATASET_NAME],
            top_k=top_k,
        )
    results = score_chunks(chunks, top_k=top_k)
    results.sort(key=lambda r: r.score, reverse=True)
    return {"query": query, "results": [_result_to_dict(r) for r in results]}
