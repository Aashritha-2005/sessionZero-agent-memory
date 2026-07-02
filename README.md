# cognee-agent-memory

**Trust-calibrated memory for AI coding agents.**
Built for *The Hangover Part AI: Where's My Context?* (WeMakeDevs x Cognee hackathon, June 29 – July 5, 2026).

> Every new AI coding agent session starts with total amnesia. You explain the same architecture decision three times. The agent forgets why you rejected an approach last week and suggests it again. Worse — if you *do* bolt memory onto an agent, a wrong or stale memory gets injected with the same confidence as a correct one, and the agent confidently repeats an old mistake.
>
> cognee-agent-memory fixes both problems: it remembers, **and it tells you how sure it is and why.**

---

## The problem

AI coding agents (Claude Code, Codex, etc.) have no memory across sessions. Bolting on a naive memory layer doesn't actually fix the underlying failure mode — it just changes *what* gets confidently repeated. If a memory is stale or has been superseded by a later decision, most memory layers will still hand it to the agent with full confidence, and the agent will act on it exactly as if it were current.

cognee-agent-memory is a memory layer built on top of [Cognee](https://www.cognee.ai)'s knowledge-graph memory lifecycle (`remember` / `recall` / `improve`+`memify` / `forget`), with one addition: every recalled memory is trust-scored and labeled **HIGH / MEDIUM / LOW confidence** before it ever reaches the agent. A stale, contradicted memory doesn't get silently dropped *or* silently trusted — it gets surfaced with a visible warning, so the human (or the agent) can decide.

---

## Architecture

```
demo-data/commits.jsonl (synthetic-but-realistic commit history)
        │
        ▼
  ingest/git_reader.py, memory_units.py   — structure commits into
        │                                    "memory units" with provenance
        ▼
  ingest/remember_client.py  ──remember()──▶  Cognee Cloud knowledge graph
        │                                              │
        │                                              ▼
  consolidate/memify_job.py                   (see "Cognee API usage" below —
  (recall()+forget()-based                      improve()/memify() are SDK-only
   consolidation, see below)                    on Cognee Cloud, so this step
        │                                        is a real, honest adaptation)
        │                                              │
  DEV WORKS IN CLAUDE CODE ──UserPromptSubmit hook──▶  RECALL (Cognee recall())
        │                                              │
        │                                              ▼
        │                                     TRUST SCORING (recall_service/trust_score.py)
        │                                     - path length (Cognee's topological_rank)
        │                                     - similarity (CHUNKS rank position)
        │                                     - recency decay (30-day half-life)
        │                                     - contradiction penalty
        │                                              │
        ◀── claude_code_bridge/bridge.py injects ──────┘
             labeled context + confidence into the session
        │
        ▼
  prune/forget_watcher.py ──forget()──▶  removes graph nodes tied to
  (triggered on file/decision deletion)   deleted files or superseded decisions

  dashboard/index.html — timeline, confidence color-coding,
  provenance drill-down, manual "forget this" button (real forget())
```

### Components

| Path | What it does |
|---|---|
| `ingest/` | Reads commit history (`demo-data/commits.jsonl`), structures it into "memory units" (decisions, bug+fix pairs, reverts, contradictions, deletions) with provenance, calls real `remember()` |
| `recall_service/` | `trust_score.py` — the four-signal scoring function; `api.py` — FastAPI `/recall`, `/timeline`, `/forget` |
| `consolidate/` | `memify_job.py` — consolidation, reframed to `recall()`+`forget()` (see below) |
| `prune/` | `forget_watcher.py` — detects deleted/superseded memories, calls real `forget()` |
| `claude_code_bridge/` | `bridge.py` — a real Claude Code `UserPromptSubmit` hook that injects trust-labeled recall context before the agent responds |
| `dashboard/` | `index.html` — single-page timeline UI, no build step |
| `demo-data/` | Synthetic-but-realistic commit history + session transcripts for a fictional project ("ShiftLog"), generated for this demo rather than pulled from a real external repo |

---

## Why a synthetic demo project ("ShiftLog")?

The demo data is deliberately synthetic rather than pulled from a real external repository — this keeps the project fully self-contained and reviewable without needing access to any other codebase. It's designed to be *realistic*, not simplistic: 15 commits spanning architecture decisions, bug fixes, a reverted approach (Redis pub/sub → polling), and two independent contradiction cases (a database-hosting decision and an auth-approach decision), so the trust-scoring and consolidation logic has genuine cases to reason about, not synthetic scoring inputs made up after the fact.

---

## Cognee API usage

This project deliberately exercises Cognee's memory lifecycle as deeply as the hosted Cognee Cloud API allows — and is explicit about where the hosted API's real surface differs from the full SDK.

| API | How it's used here | Status |
|---|---|---|
| **`remember()`** | Every commit becomes a "memory unit" (decision, bug+fix, revert, contradiction, or deletion) and is ingested via a real call to Cognee Cloud's `/api/v1/remember`. 15 memory units ingested across two batches. | ✅ Real, verified |
| **`recall()`** | Queried live by `claude_code_bridge/bridge.py` before every coding-session prompt, by `recall_service/api.py`'s `/recall` and `/timeline` endpoints, and directly in `trust_score.py`'s scoring pipeline. Uses Cognee's `CHUNKS` search type for ranked, scorable results. | ✅ Real, verified |
| **`forget()`** | Triggered on two kinds of real events: (1) a file/feature deletion commit (`prune/forget_watcher.py`), and (2) a memory unit that a newer, contradicting memory unit supersedes (`consolidate/memify_job.py`). Both were verified with real before/after `recall()` diffs proving the graph actually changed, not just that an API call returned 200. Also manually triggerable from the dashboard. | ✅ Real, verified |
| **`improve()` / `memify()`** | **Honest limitation, not a workaround.** Verified two independent ways — the tenant's live `GET /openapi.json`, and Cognee's own docs at docs.cognee.ai/api-reference — that `improve()`/`memify()` are **SDK-only**: they take live Python objects and are architecturally not exposed as HTTP endpoints on Cognee Cloud. Calling the in-process SDK functions would build a disconnected *local* graph (needing its own separate LLM key) rather than operate on the real ingested cloud dataset, so it wouldn't demonstrate anything real. **Consolidation is instead implemented as a legitimate adaptation**: `consolidate/memify_job.py`'s `consolidate_contradictions()` uses the same reference graph `ingest/memory_units.py` extracts from commit messages, resolves each superseded memory's real Cognee `data_id`, and calls real `forget()` — achieving the same practical outcome (stale/contradicted knowledge is pruned) within what the hosted API actually supports. | ⚠️ SDK-only on Cognee Cloud — reframed via `recall()`+`forget()`, not called directly |

We'd rather show you exactly where the hosted API's real boundary is than claim four-for-four when one of those calls would have been fake.

---

## Trust scoring

`recall_service/trust_score.py` combines four signals into one score, deliberately kept as a simple, explainable weighted mean rather than anything opaque:

1. **`path_length_score`** — from Cognee's real `topological_rank` field on graph search results. Shorter path = more directly connected = higher trust.
2. **`similarity_score`** — Cognee Cloud's `CHUNKS` search returns pre-ranked results but no raw cosine score in this API version (`score: null`), so we use rank position as the similarity proxy: top-ranked result scores near 1.0.
3. **`recency_score`** — exponential decay from the memory's source-commit timestamp, 30-day half-life.
4. **`contradiction_penalty`** — a flat penalty applied when a newer ingested memory explicitly supersedes this one (tracked via reference extraction from commit messages, not from Cognee directly).

```
score = mean(path_length, similarity, recency) × (1 − contradiction_penalty)
```

clipped to `[0, 1]`, labeled **HIGH** (≥0.7) / **MEDIUM** (≥0.4) / **LOW — verify before trusting** (below 0.4).

**Verified example** (real data, not a synthetic test case): for the query *"Does ShiftLog use JWT for authentication?"*, the correct, current decision (session cookies) scored **0.99 HIGH**, while the old, superseded JWT decision — still semantically on-topic — scored only **0.28 LOW**, flagged with a contradiction warning instead of silently injected.

---

## Setup

```bash
git clone <this-repo> && cd cognee-agent-memory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in COGNEE_API_KEY, COGNEE_API_BASE_URL, COGNEE_TENANT_ID from your Cognee Cloud tenant

# ingest the demo data (real remember() calls, takes a few minutes)
python3 -m ingest.remember_client

# sanity check
python3 -m ingest.recall_check

# run the recall API + dashboard
.venv/bin/uvicorn recall_service.api:app --host 127.0.0.1 --port 8000 &
python3 -m http.server 5173 --directory dashboard &
# open http://127.0.0.1:5173/index.html

# run tests
python3 -m pytest recall_service/tests/ claude_code_bridge/tests/ -v
```

The `claude_code_bridge/bridge.py` hook is wired into `.claude/settings.json` as a `UserPromptSubmit` hook — opening this project in Claude Code will inject trust-labeled recall context before every prompt automatically.

---

## AI Assistance Disclosure

Built with assistance from **Claude Code** for implementation — including the ingestion pipeline, trust-scoring logic, Cognee Cloud API integration, the Claude Code bridge, the dashboard, and this README. Architecture, trust-scoring design, project direction, and all API-usage/limitation decisions (e.g. the `improve()`/`memify()` reframing) were directed by **Aashritha Lakshmi Mallampati**, who reviewed and approved each stage before proceeding to the next.

---

## Non-negotiables this project followed

- No mocked Cognee calls — every `remember()`/`recall()`/`forget()` claim in this README is backed by a real API call, verified with raw output (see `PROJECT_PLAN.md`'s `CURRENT STATUS` log for the full trail).
- Trust scoring is a simple weighted mean, not an opaque model — a judge should be able to read the four signals above and understand each in one sentence.
- Where the real hosted API had a gap (`improve()`/`memify()`), we said so plainly rather than routing around it silently.
