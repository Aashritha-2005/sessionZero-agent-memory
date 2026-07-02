"""Trust scoring for recalled memories.

Four signals, weighted and combined into one explainable number:

1. **path_length_score** — how directly connected the memory is in
   Cognee's knowledge graph. We use the real `topological_rank` field
   Cognee returns on each chunk (lower rank = more central/direct =
   higher trust). Score = 1 / (1 + topological_rank).

2. **similarity_score** — how semantically relevant the memory is to
   the query. Cognee Cloud's CHUNKS search doesn't expose a raw cosine
   score in this API version (`score` comes back null), but it *does*
   return chunks pre-ranked by relevance — so we use rank position as
   the similarity proxy: the top-ranked chunk scores near 1.0, decaying
   toward 0 by top_k.

3. **recency_score** — exponential decay based on the memory's age
   (days since its source commit), computed from our own ingestion-time
   provenance (the commit timestamp we embedded in the memory body),
   not from Cognee. Half-life is configurable (default 30 days).

4. **contradiction_penalty** — if a newer ingested memory explicitly
   supersedes/reverts this one (tracked via the `references` field
   `ingest/memory_units.py` already extracts from commit messages),
   we apply a flat penalty. This is our own provenance graph, not
   Cognee's — Cognee stores the *content*, we track the *relationship*.

Combination: score = mean(path, similarity, recency) * (1 - contradiction_penalty)
then clipped to [0, 1]. Kept as a simple weighted/discounted mean on
purpose (see PROJECT_PLAN.md §7) — a judge should be able to read this
docstring and understand every signal in one sentence.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from ingest.memory_units import MemoryUnit, build_memory_units

_COMMIT_LINE_RE = re.compile(r"Commit:\s*([0-9a-f]{7})\s*\(([^)]+)\)")

HIGH_THRESHOLD = 0.7
MEDIUM_THRESHOLD = 0.4
RECENCY_HALF_LIFE_DAYS = 30.0
CONTRADICTION_PENALTY = 0.6


@dataclass(frozen=True)
class TrustSignals:
    path_length_score: float
    similarity_score: float
    recency_score: float
    contradiction_penalty: float


@dataclass(frozen=True)
class TrustResult:
    source_commit: str
    text: str
    signals: TrustSignals
    score: float
    label: str  # HIGH | MEDIUM | LOW


def label_for_score(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "HIGH CONFIDENCE"
    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM CONFIDENCE"
    return "LOW — verify before trusting"


def extract_commit_hash(chunk_text: str) -> str | None:
    """Pull the source commit hash back out of a recalled chunk's text.

    We embed `Commit: <hash> (<timestamp>)` in every memory unit body at
    ingestion time (see ingest/memory_units.py), so this is exact, not a
    heuristic — as long as the chunk text came from our ingestion.
    """
    m = _COMMIT_LINE_RE.search(chunk_text)
    return m.group(1) if m else None


def path_length_score(topological_rank: int | None) -> float:
    if topological_rank is None:
        return 0.5  # neutral default when the API doesn't return one
    return 1.0 / (1.0 + max(0, topological_rank))


def similarity_score(rank: int, top_k: int) -> float:
    """Rank-position proxy for semantic similarity (0-indexed rank)."""
    if top_k <= 1:
        return 1.0
    return max(0.0, 1.0 - (rank / top_k))


def recency_score(
    commit_timestamp: datetime,
    as_of: datetime | None = None,
    half_life_days: float = RECENCY_HALF_LIFE_DAYS,
) -> float:
    as_of = as_of or datetime.now(timezone.utc)
    age_days = max(0.0, (as_of - commit_timestamp).total_seconds() / 86400.0)
    return math.exp(-math.log(2) * age_days / half_life_days)


def build_contradiction_index(units: list[MemoryUnit] | None = None) -> dict[str, list[str]]:
    """Map source_commit -> list of commit hashes of memories that supersede it.

    A memory unit of kind "revert" or "contradiction" that references an
    older commit hash marks that older commit as contradicted.
    """
    units = units if units is not None else build_memory_units()
    contradicted_by: dict[str, list[str]] = {}
    for unit in units:
        if unit.kind not in ("revert", "contradiction"):
            continue
        for ref in unit.references:
            contradicted_by.setdefault(ref, []).append(unit.source_commit)
    return contradicted_by


def contradiction_penalty_for(commit_hash: str, contradiction_index: dict[str, list[str]]) -> float:
    return CONTRADICTION_PENALTY if commit_hash in contradiction_index else 0.0


def combine(signals: TrustSignals) -> float:
    base = (signals.path_length_score + signals.similarity_score + signals.recency_score) / 3.0
    score = base * (1.0 - signals.contradiction_penalty)
    return max(0.0, min(1.0, score))


def score_chunks(
    chunks: list[dict],
    top_k: int,
    memory_units: list[MemoryUnit] | None = None,
    as_of: datetime | None = None,
) -> list[TrustResult]:
    """Score a list of raw CHUNKS-search results from cognee recall().

    `chunks` is the raw list returned by CogneeApiClient.recall(...,
    search_type="CHUNKS"), in ranked order (first = most relevant).
    """
    memory_units = memory_units if memory_units is not None else build_memory_units()
    units_by_commit = {u.source_commit: u for u in memory_units}
    contradiction_index = build_contradiction_index(memory_units)

    results = []
    for rank, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        commit_hash = extract_commit_hash(text)
        raw_meta = chunk.get("raw", {}) or {}
        topo_rank = raw_meta.get("topological_rank")

        unit = units_by_commit.get(commit_hash) if commit_hash else None
        commit_ts = unit.timestamp if unit else None

        signals = TrustSignals(
            path_length_score=path_length_score(topo_rank),
            similarity_score=similarity_score(rank, top_k),
            recency_score=recency_score(commit_ts, as_of=as_of) if commit_ts else 0.5,
            contradiction_penalty=(
                contradiction_penalty_for(commit_hash, contradiction_index) if commit_hash else 0.0
            ),
        )
        score = combine(signals)
        results.append(
            TrustResult(
                source_commit=commit_hash or "unknown",
                text=text,
                signals=signals,
                score=score,
                label=label_for_score(score),
            )
        )
    return results
