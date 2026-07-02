from datetime import datetime, timedelta, timezone

from ingest.memory_units import MemoryUnit
from recall_service.trust_score import (
    HIGH_THRESHOLD,
    MEDIUM_THRESHOLD,
    TrustSignals,
    build_contradiction_index,
    combine,
    contradiction_penalty_for,
    extract_commit_hash,
    label_for_score,
    path_length_score,
    recency_score,
    similarity_score,
    score_chunks,
)


def _unit(source_commit, kind="decision", references=(), timestamp=None):
    return MemoryUnit(
        id=f"mu-{source_commit}",
        kind=kind,
        title="t",
        body=f"[{kind}] body\nCommit: {source_commit} ({(timestamp or datetime(2026, 1, 1, tzinfo=timezone.utc)).isoformat()})",
        files=[],
        timestamp=timestamp or datetime(2026, 1, 1, tzinfo=timezone.utc),
        source_commit=source_commit,
        references=list(references),
    )


# -- path_length_score -------------------------------------------------


def test_path_length_score_zero_rank_is_max_trust():
    assert path_length_score(0) == 1.0


def test_path_length_score_decreases_with_distance():
    assert path_length_score(1) < path_length_score(0)
    assert path_length_score(3) < path_length_score(1)


def test_path_length_score_missing_defaults_neutral():
    assert path_length_score(None) == 0.5


# -- similarity_score ----------------------------------------------------


def test_similarity_score_top_rank_is_max():
    assert similarity_score(rank=0, top_k=10) == 1.0


def test_similarity_score_decreases_with_rank():
    assert similarity_score(rank=5, top_k=10) < similarity_score(rank=0, top_k=10)


def test_similarity_score_never_negative():
    assert similarity_score(rank=99, top_k=10) == 0.0


# -- recency_score --------------------------------------------------------


def test_recency_score_fresh_is_near_one():
    now = datetime(2026, 7, 2, tzinfo=timezone.utc)
    assert recency_score(now, as_of=now) == 1.0


def test_recency_score_decays_over_half_life():
    now = datetime(2026, 7, 2, tzinfo=timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    score = recency_score(thirty_days_ago, as_of=now, half_life_days=30.0)
    assert abs(score - 0.5) < 1e-6


def test_recency_score_older_is_always_lower():
    now = datetime(2026, 7, 2, tzinfo=timezone.utc)
    recent = now - timedelta(days=5)
    old = now - timedelta(days=90)
    assert recency_score(old, as_of=now) < recency_score(recent, as_of=now)


# -- contradiction penalty -------------------------------------------------


def test_contradiction_index_flags_reverted_commit():
    units = [
        _unit("aaa1111", kind="decision"),
        _unit("bbb2222", kind="revert", references=["aaa1111"]),
    ]
    index = build_contradiction_index(units)
    assert "aaa1111" in index
    assert index["aaa1111"] == ["bbb2222"]


def test_contradiction_index_ignores_unrelated_commits():
    units = [
        _unit("aaa1111", kind="decision"),
        _unit("ccc3333", kind="decision"),
    ]
    index = build_contradiction_index(units)
    assert index == {}


def test_contradiction_penalty_applied_only_when_contradicted():
    index = {"aaa1111": ["bbb2222"]}
    assert contradiction_penalty_for("aaa1111", index) > 0.0
    assert contradiction_penalty_for("ccc3333", index) == 0.0


# -- combine / labels -------------------------------------------------------


def test_combine_no_contradiction_is_plain_mean():
    signals = TrustSignals(
        path_length_score=1.0, similarity_score=1.0, recency_score=1.0, contradiction_penalty=0.0
    )
    assert combine(signals) == 1.0


def test_combine_contradiction_discounts_score():
    clean = TrustSignals(
        path_length_score=0.8, similarity_score=0.8, recency_score=0.8, contradiction_penalty=0.0
    )
    contradicted = TrustSignals(
        path_length_score=0.8, similarity_score=0.8, recency_score=0.8, contradiction_penalty=0.6
    )
    assert combine(contradicted) < combine(clean)


def test_combine_clips_to_zero_one():
    signals = TrustSignals(
        path_length_score=1.0, similarity_score=1.0, recency_score=1.0, contradiction_penalty=1.0
    )
    assert combine(signals) == 0.0


def test_label_thresholds():
    assert label_for_score(HIGH_THRESHOLD) == "HIGH CONFIDENCE"
    assert label_for_score(MEDIUM_THRESHOLD) == "MEDIUM CONFIDENCE"
    assert label_for_score(0.0) == "LOW — verify before trusting"


# -- extract_commit_hash ------------------------------------------------


def test_extract_commit_hash_finds_hash():
    text = "[decision] blah\nCommit: a1f3c02 (2026-05-04T10:12:00+00:00) by aashritha"
    assert extract_commit_hash(text) == "a1f3c02"


def test_extract_commit_hash_missing_returns_none():
    assert extract_commit_hash("no commit line here") is None


# -- score_chunks integration (no network — synthetic chunk payloads) -----


def test_score_chunks_contradicted_unit_scores_lower_than_clean():
    now = datetime(2026, 7, 2, tzinfo=timezone.utc)
    old = _unit("aaa1111", kind="decision", timestamp=now - timedelta(days=10))
    newer = _unit("bbb2222", kind="contradiction", references=["aaa1111"], timestamp=now - timedelta(days=1))
    clean = _unit("ccc3333", kind="decision", timestamp=now - timedelta(days=10))
    units = [old, newer, clean]

    chunks = [
        {"text": old.body, "raw": {"topological_rank": 0}},
        {"text": clean.body, "raw": {"topological_rank": 0}},
    ]
    results = score_chunks(chunks, top_k=2, memory_units=units, as_of=now)

    old_result = next(r for r in results if r.source_commit == "aaa1111")
    clean_result = next(r for r in results if r.source_commit == "ccc3333")

    assert old_result.signals.contradiction_penalty > 0.0
    assert clean_result.signals.contradiction_penalty == 0.0
    assert old_result.score < clean_result.score
