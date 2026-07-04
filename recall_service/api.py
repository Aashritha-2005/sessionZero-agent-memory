"""FastAPI wrapper exposing trust-scored recall over HTTP.

GET  /health     — passthrough to the real Cognee Cloud tenant's health check.
GET  /recall     — real Cognee CHUNKS recall, trust-scored, for a query.
GET  /summaries  — real Cognee SUMMARIES search — condensed bullet-point
                    summaries of matching memories, not scored (see its
                    own docstring for why it deliberately doesn't touch
                    trust_score.py).
GET  /timeline   — every ingested memory, chronological, with a
                    query-independent baseline trust score for the
                    dashboard's confidence color-coding, and whether it's
                    still live in the graph or already forgotten.
POST /forget     — real forget() on a memory unit by commit hash, for the
                    dashboard's manual "forget this" button.

This is what claude_code_bridge/bridge.py calls before a coding task, and
what the dashboard calls to browse memories/provenance/prune.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from ingest.dataset_index import build_commit_to_data_id, get_dataset_id
from ingest.memory_units import build_memory_units
from ingest.remember_client import DATASET_NAME, _client
from recall_service.trust_score import (
    TrustResult,
    TrustSignals,
    build_contradiction_index,
    combine,
    label_for_score,
    path_length_score,
    recency_score,
    score_chunks,
)

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"

# Scoped to this endpoint only, deliberately not reused from trust_score.py's
# extract_commit_hash(): that one requires the exact "Commit: <hash> (<ts>)"
# format we embed in our own memory bodies, but Cognee's SUMMARIES output is
# free-form prose that mentions hashes loosely (e.g. "commit 2c9e4f1 on
# 2026-06-10..."). A bare 7-hex-char match is low-stakes here — worst case
# is a wrong-but-plausible commit shown next to a summary, not a scoring or
# pruning decision — so it doesn't need trust_score.py's stricter guard.
_LOOSE_HASH_RE = re.compile(r"\b[0-9a-f]{7}\b")


def _loose_commit_hash(text: str) -> str | None:
    m = _LOOSE_HASH_RE.search(text)
    return m.group(0) if m else None

app = FastAPI(title="cognee-agent-memory recall_service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _result_to_dict(r: TrustResult) -> dict:
    return {
        "source_commit": r.source_commit,
        "text": r.text,
        "score": round(r.score, 3),
        "label": r.label,
        "signals": r.signals.__dict__,
    }


@app.get("/")
def dashboard():
    """Serves dashboard/index.html directly from this backend, so a
    single Railway deploy covers both the API and the UI — no separate
    static host needed."""
    return FileResponse(DASHBOARD_DIR / "index.html")


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


@app.get("/summaries")
def summaries(query: str = Query(...), top_k: int = Query(5, ge=1, le=20)):
    """Real Cognee `SUMMARIES` search — condensed, bullet-point summaries
    of matching memories, genuinely different output from CHUNKS (raw
    text) or the GRAPH_COMPLETION style answer /recall's trust-scoring
    is built on.

    Deliberately NOT trust-scored: SUMMARIES results don't carry the
    same per-chunk `topological_rank`/ranked-list shape score_chunks()
    expects, and retrofitting trust_score.py to score a different
    result shape would mean touching its already-verified logic — out
    of scope for this addition. Returned as plain real Cognee output
    with basic provenance (source commit, if extractable) so the
    dashboard can show it without implying a confidence label that
    isn't real.
    """
    with _client() as client:
        results = client.recall(
            query=query,
            search_type="SUMMARIES",
            datasets=[DATASET_NAME],
            top_k=top_k,
        )
    out = []
    for r in results:
        text = r.get("text", "")
        commit = _loose_commit_hash(text)
        out.append({"text": text, "source_commit": commit})
    return {"query": query, "results": out}


@app.get("/timeline")
def timeline():
    """Every memory unit, chronological, with a *query-independent*
    baseline trust score (similarity is set to 1.0/neutral since there's
    no active query in a timeline view — path/recency/contradiction are
    the only signals that make sense outside a specific query)."""
    units = build_memory_units()
    contradiction_index = build_contradiction_index(units)

    with _client() as client:
        client.health()
        dataset_id = get_dataset_id(client, DATASET_NAME)
        commit_to_data_id = build_commit_to_data_id(client, dataset_id)

    entries = []
    for unit in sorted(units, key=lambda u: u.timestamp):
        contradiction_penalty = 0.6 if unit.source_commit in contradiction_index else 0.0
        signals = TrustSignals(
            path_length_score=path_length_score(0),
            similarity_score=1.0,
            recency_score=recency_score(unit.timestamp),
            contradiction_penalty=contradiction_penalty,
        )
        score = combine(signals)
        is_live = unit.source_commit in commit_to_data_id
        entries.append(
            {
                "id": unit.id,
                "source_commit": unit.source_commit,
                "kind": unit.kind,
                "title": unit.title,
                "files": unit.files,
                "timestamp": unit.timestamp.isoformat(),
                "references": unit.references,
                "superseded_by": contradiction_index.get(unit.source_commit, []),
                "score": round(score, 3),
                "label": label_for_score(score),
                "signals": signals.__dict__,
                "status": "live" if is_live else "forgotten",
                "data_id": commit_to_data_id.get(unit.source_commit),
            }
        )
    return {"dataset": DATASET_NAME, "count": len(entries), "entries": entries}


@app.post("/forget")
def forget(commit: str = Query(..., description="Source commit hash of the memory to forget")):
    units = {u.source_commit: u for u in build_memory_units()}
    unit = units.get(commit)
    if not unit:
        raise HTTPException(status_code=404, detail=f"No memory unit for commit '{commit}'")

    with _client() as client:
        client.health()
        dataset_id = get_dataset_id(client, DATASET_NAME)
        commit_to_data_id = build_commit_to_data_id(client, dataset_id)
        data_id = commit_to_data_id.get(commit)
        if not data_id:
            raise HTTPException(
                status_code=409, detail=f"Commit '{commit}' has no live data_id — already forgotten?"
            )
        result = client.forget(dataset=DATASET_NAME, data_id=data_id)

    return {"commit": commit, "title": unit.title, "data_id": data_id, "forget_result": result}
