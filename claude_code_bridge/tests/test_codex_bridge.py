from claude_code_bridge.codex_bridge import INJECT_FLOOR, MAX_INJECTED, format_context_block


def _result(commit, score, contradiction_penalty=0.0, label=None, text="[decision] example\nCommit: x"):
    return {
        "source_commit": commit,
        "text": text,
        "score": score,
        "label": label or ("HIGH CONFIDENCE" if score >= 0.7 else "LOW — verify before trusting"),
        "signals": {
            "path_length_score": 1.0,
            "similarity_score": score,
            "recency_score": 1.0,
            "contradiction_penalty": contradiction_penalty,
        },
    }


def test_empty_results_produces_empty_block():
    assert format_context_block([]) == ""


def test_below_floor_results_are_excluded():
    results = [_result("aaa1111", score=INJECT_FLOOR - 0.05)]
    assert format_context_block(results) == ""


def test_top_results_are_included_up_to_max():
    results = [_result(f"c{i}", score=0.9 - i * 0.05) for i in range(MAX_INJECTED + 2)]
    block = format_context_block(results)
    included = sum(1 for r in results[:MAX_INJECTED] if r["source_commit"] in block)
    assert included == MAX_INJECTED


def test_contradicted_result_surfaces_even_outside_top_n():
    clean = [_result(f"clean{i}", score=0.9 - i * 0.01) for i in range(MAX_INJECTED)]
    contradicted = _result("stale1", score=0.25, contradiction_penalty=0.6)
    block = format_context_block(clean + [contradicted])
    assert "stale1" in block
    assert "verify before relying on it" in block
