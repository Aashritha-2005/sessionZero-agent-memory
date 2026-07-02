# cognee-agent-memory — Trust-Calibrated Memory for AI Coding Agents
## Master Build Plan for "The Hangover Part AI: Where's My Context?" (Cognee x WeMakeDevs Hackathon)

> **READ THIS ENTIRE FILE BEFORE WRITING OR EDITING ANY CODE.**
> This file is the single source of truth for the project. It contains the rules we must never violate, the architecture, the day-by-day plan, and a live STATUS block that must be updated after every work session. If you (Claude Code) are picking this up mid-project, go straight to `## CURRENT STATUS` at the bottom, read it, and resume from the exact next unchecked task. Do not re-plan or re-architect unless explicitly asked.

---

## 0. HACKATHON META (do not violate these — disqualification risk)

- **Event:** The Hangover Part AI: Where's My Context? — WeMakeDevs x Cognee
- **Dates:** June 29 – July 5, 2026 (today is July 2, 2026 — ~3 days left)
- **Submission deadline:** July 5, 2026 (end of day — confirm exact time on the Schedule tab before final push, do not assume)
- **Team:** Solo (Aashritha)

### 0.1 Hard Rules — violating any of these can get us disqualified

1. **Must use Cognee for memory.** Not optional, not a side feature — it must be the core memory mechanism of the project. Judged explicitly on "Best Use of Cognee."
2. **Coding/design work must not have started before the hackathon officially opened (June 29).** We are fine — building now, well within window. Do not backdate commits or claim earlier work.
3. **AI assistant use (Claude Code, Codex) is allowed but MUST be disclosed in the submission.** Non-disclosure = disqualification. → We will add an explicit "AI Assistance Disclosure" section to the README (see §6).
4. **No spamming the Cognee GitHub repo.** If we attempt the Open Source Track (optional, stretch goal only): max 5 PRs per person, no typo-only/whitespace/auto-generated PRs, must comment + get assigned before working an issue. **Do not touch this track unless main project is done early** — it's a distraction from the core prize.
5. **Original work only on top of allowed third-party tools/libraries/APIs/CC assets.** Fine to use open-source libs (React, FastAPI, etc.) — just don't claim someone else's project as ours.
6. **No harassment/discrimination in any team or public communication** (n/a for solo, but applies to Discord/social presence too).
7. **IP belongs to us** (solo team) — no conflict here.
8. **Job interview ≠ guaranteed job** — just context, not a rule we can break, but don't oversell this in any public messaging.

### 0.2 What "winning" requires (mapped from judging criteria — keep this visible at all times)

| Criterion | What Judges Are Actually Scoring | Our Answer |
|---|---|---|
| Potential Impact | Does it solve a real, painful problem? | Context loss in AI coding agents — a problem every dev using Claude Code/Codex has today |
| Creativity & Innovation | Is this novel, not just "chatbot remembers stuff"? | Trust-calibrated recall (confidence scoring + provenance) — nobody else will build this |
| Technical Excellence | Code quality, engineering depth | Clean modular architecture, real ingestion pipeline, real calibration math, tests |
| Best Use of Cognee | Depth of use of remember/recall/improve-memify/forget | We deliberately exercise ALL FOUR lifecycle APIs with clear justification for each |
| User Experience | Is the output usable/understandable? | Timeline dashboard makes invisible memory visible; CLI is simple |
| Presentation Quality | Demo clarity, README, storytelling | Script the demo around the literal "agent forgets" pain point; polished README with GIF/video |

---

## 1. PROJECT DEFINITION

**Name:** cognee-agent-memory

**One-liner:** A Cognee-powered memory layer for AI coding agents (Claude Code / Codex) that remembers past architecture decisions, bugs, and their fixes across sessions and repos — and unlike a plain memory bot, every recalled fact carries a calibrated trust score and a visible provenance path, so the agent never silently injects stale or wrong context.

**The problem statement (use this exact framing in the README and demo — it mirrors the hackathon's own "hangover" theme):**
> Every new AI coding agent session starts with total amnesia. You explain the same architecture decision three times. The agent forgets why you rejected an approach last week and suggests it again. Worse — if you *do* bolt memory onto an agent, a wrong or stale memory gets injected with the same confidence as a correct one, and the agent confidently repeats an old mistake. cognee-agent-memory fixes both problems: it remembers, and it tells you *how sure it is* and *why*.

**Why this project and not a generic "chatbot with memory":**
- Directly usable by us (dogfooding with real repos: HireScript, TaskFlow, portfolio site) — real data, not synthetic demo filler.
- The confidence/provenance layer is a genuine technical contribution, raising the ceiling on "Technical Excellence" and "Creativity."
- Cognee's four lifecycle APIs (`remember`, `recall`, `improve`/`memify`, `forget`) all have a clear, non-forced justification in this design — maximizes "Best Use of Cognee" score.

---

## 2. ARCHITECTURE

### 2.1 High-level flow

```
[Git repo: commits, PR diffs, session transcripts]
        │
        ▼
  INGESTION LAYER  ──uses Cognee remember()──▶  Cognee Knowledge Graph
        │                                              │
        │                                              ▼
        │                                     CONSOLIDATION LAYER
        │                                     (Cognee improve()/memify()
        │                                      — merge duplicates, decay
        │                                      stale weight, dedupe
        │                                      contradictions)
        │                                              │
  DEV WORKS IN CLAUDE CODE / CODEX ──query──▶  RECALL LAYER (Cognee recall())
        │                                              │
        │                                              ▼
        │                                     TRUST SCORING LAYER (ours)
        │                                     - path-length score
        │                                     - embedding similarity
        │                                     - recency decay
        │                                     - contradiction penalty
        │                                              │
        ◀──────── injected context + confidence label ─┘
        │
        ▼
  PRUNING LAYER (Cognee forget()) — triggered when files are
  deleted/refactored, removes stale graph nodes tied to that path

        ▼
  TIMELINE DASHBOARD (small web UI) — shows what's remembered,
  confidence, provenance, and lets dev manually forget/correct
```

### 2.2 Components to build

1. **`ingest/` — Ingestion pipeline**
   - Reads git log (`git log --stat`, `git show` for diffs), commit messages, and (optionally) exported Claude Code / Codex session transcripts.
   - Extracts discrete "memory units": architecture decisions, bug + fix pairs, rejected approaches (rejected approaches inferred from revert commits / commit messages containing "revert", "instead of", "changed from").
   - Calls Cognee `remember()` to ingest each memory unit, tagged with file path(s), timestamp, and source commit hash.

2. **`recall_service/` — Recall + trust scoring**
   - Wraps Cognee `recall()`.
   - For each recalled item, computes a **trust score** from:
     - Graph path length (shorter = more directly connected = higher trust)
     - Embedding similarity score (from Cognee's vector layer)
     - Recency decay (older memories decay unless reinforced)
     - Contradiction penalty (if a newer memory conflicts with an older one on the same file/topic, downweight the older one)
   - Returns results labeled: `HIGH CONFIDENCE`, `MEDIUM`, `LOW — verify before trusting`.
   - Exposes a simple API (`/recall?query=...&file=...`) that Claude Code / Codex can call via the existing Cognee agentic integration (MCP-style) or a lightweight wrapper script.

3. **`consolidate/` — Scheduled job**
   - Calls Cognee `improve()` / `memify()` after each ingestion batch.
   - Detects duplicate/contradictory memories (e.g., "we use Postgres" vs later "we moved to Railway/Postgres-on-Railway") and merges/reweights.

4. **`prune/` — Forget trigger**
   - Watches for deleted/renamed files (git diff on each ingestion run).
   - Calls Cognee `forget()` to surgically remove graph nodes tied to now-deleted paths, with a log of what was forgotten and why (for transparency in the dashboard).

5. **`dashboard/` — Timeline UI**
   - Small React app (or HTML/JS single page — keep it simple given the time budget).
   - Views: Memory Timeline (chronological), Confidence view (color-coded by trust score), Provenance drill-down (click a memory → see source commit/diff), manual "forget this" button.

6. **`claude_code_bridge/` — Integration glue**
   - Uses Cognee's existing Claude Code integration guide (linked in hackathon Resources tab) as the base.
   - Before a coding task, auto-queries `recall_service` for the touched file(s) and injects labeled context into the agent's working context.
   - This is the "wow" moment for the demo: show Claude Code getting a HIGH CONFIDENCE recall right, and a LOW CONFIDENCE recall correctly flagged instead of blindly trusted.

### 2.3 Tech stack

- **Memory backend:** Cognee (self-hosted or Cognee Cloud — we already have $37.50 dev credit redeemed)
- **Ingestion / backend services:** Python (FastAPI for the recall API)
- **Trust scoring:** plain Python — no need for heavy ML; a weighted-sum or simple logistic function over the four signals is enough and easy to explain to judges (explainability > complexity here)
- **Dashboard:** React + Tailwind (reuse patterns from the portfolio site build) or a simpler static HTML/JS page if time is short by Day 3
- **Agent integration:** Cognee's official Claude Code integration guide + Codex integration guide (both linked in hackathon Resources)
- **Demo data:** Self-contained sample data generated **inside this project folder only** (e.g. `demo-data/`) — a small set of realistic-looking commits, decisions, and session transcripts written as fixture files. **Do not read from, cd into, or otherwise touch any other project folder (HireScript, TaskFlow, portfolio, or any repo outside `cognee-agent-memory/`).** All ingestion, testing, and demo data must be scoped strictly to this project's own directory.

---

## 3. HOW EACH COGNEE API IS USED (write this explicitly in the README — this is a scored criterion)

- **`remember()`** — ingest commit history, diffs, and session transcripts as structured memory units tagged by file path and timestamp.
- **`recall()`** — queried live by the Claude Code / Codex bridge before each coding task, and by the dashboard for browsing.
- **`improve()` / `memify()`** — scheduled consolidation pass: merges duplicate memories, reweights based on how often a memory was actually retrieved and used, decays stale entries.
- **`forget()`** — triggered automatically when a file is deleted/renamed, surgically removing now-irrelevant graph nodes; also manually triggerable from the dashboard.

This is the strongest possible answer to "did you deeply use the lifecycle, or just remember+recall?" — make sure the demo actually shows all four in action, not just claims it in text.

---

## 4. DAY-BY-DAY PLAN (today: July 2, 2026 — deadline July 5, 2026)

### DAY 0 / Today (July 2) — Setup + Ingestion MVP
- [ ] Confirm exact submission deadline time on the hackathon Schedule tab
- [ ] Set up Cognee (Cloud, using existing redeemed credit) — confirm API keys work
- [ ] Scaffold repo structure (see §5)
- [ ] Build `ingest/` — pull git log + diffs from one real repo (start with HireScript or TaskFlow)
- [ ] Get first successful `remember()` calls ingesting real commit data into Cognee
- [ ] Sanity-check with a raw `recall()` query — confirm data is actually queryable
- [ ] Commit early, commit often — timestamps matter for rule compliance

### DAY 1 (July 3) — Trust Layer + Consolidation + Pruning
- [ ] Build `recall_service/` trust scoring (path length, similarity, recency decay, contradiction penalty)
- [ ] Wire `improve()`/`memify()` consolidation job — test on a repo with at least one reverted/changed decision
- [ ] Wire `forget()` pruning on deleted/renamed files
- [ ] Write unit tests for the trust scoring function (judges reward technical rigor — a tested scoring function stands out)
- [ ] Ingest a second repo to prove generality (not hardcoded to one project)

### DAY 2 (July 4) — Agent Integration + Dashboard
- [ ] Wire `claude_code_bridge/` using Cognee's official Claude Code integration guide
- [ ] Live-test: start a real Claude Code session on one of the demo repos, confirm recalled context (with confidence label) is actually injected
- [ ] Build the dashboard (timeline, confidence color-coding, provenance drill-down, manual forget button)
- [ ] Polish trust score UI labels (HIGH / MEDIUM / LOW — verify)
- [ ] Start drafting README + AI Assistance Disclosure section

### DAY 3 (July 5 — submission day, treat as morning-only work + buffer)
- [ ] Record demo video (see §6 script) — 2–3 minutes max, tight and story-driven
- [ ] Finalize README (problem, solution, architecture diagram, Cognee API usage table, setup instructions, AI disclosure)
- [ ] Optional: write hackathon blog post (covers the Best Blogs side track — near-zero extra effort since README content is 80% reusable)
- [ ] Optional: 1–2 social posts tagging @wemakedevs and Cognee (Social Buzz side track)
- [ ] Final rule-compliance check (§0.1 checklist) before submitting
- [ ] Submit with buffer time before deadline — do not submit at the last minute

---

## 5. REPO STRUCTURE

```
cognee-agent-memory/
├── PROJECT_PLAN.md          # this file
├── README.md                 # final submission README
├── ingest/
│   ├── git_reader.py         # parses git log/diffs
│   ├── memory_units.py       # structures raw data into memory units
│   └── remember_client.py    # wraps Cognee remember()
├── recall_service/
│   ├── api.py                 # FastAPI app exposing /recall
│   ├── trust_score.py         # confidence scoring logic
│   └── tests/
│       └── test_trust_score.py
├── consolidate/
│   └── memify_job.py          # scheduled improve()/memify() pass
├── prune/
│   └── forget_watcher.py      # detects deletions, calls forget()
├── claude_code_bridge/
│   └── bridge.py               # pre-task recall injection hook
├── dashboard/
│   └── (React or static app)
├── demo/
│   ├── demo_script.md
│   └── demo_video.mp4          # final recording
└── .env.example
```

---

## 6. SUBMISSION REQUIREMENTS CHECKLIST

- [ ] README with: problem statement, architecture diagram, Cognee API usage table (§3), setup instructions, demo video/GIF link
- [ ] **AI Assistance Disclosure section** (required by Rule 8) — state plainly: "Built with assistance from Claude Code and Codex for implementation; architecture, trust-scoring design, and project direction by Aashritha Lakshmi Mallampati."
- [ ] Demo video script beat sheet:
  1. Open on the pain: show an agent re-asking something already decided 3 sessions ago
  2. Cut to the memory layer in action: show `remember()` ingesting real repo history live
  3. Show a HIGH CONFIDENCE recall correctly injected into a live Claude Code session
  4. Show a LOW CONFIDENCE recall correctly flagged instead of blindly trusted (this is the key differentiator moment — dwell on it)
  5. Quick dashboard tour: timeline + provenance drill-down
  6. Close with the four-API usage summary (remember/recall/improve/forget) on screen
- [ ] Confirm no rule violations before hitting submit (re-check §0.1)

---

## 7. NON-NEGOTIABLE PRINCIPLES WHILE BUILDING

- Do not fake or mock Cognee calls for the demo — judges score "Best Use of Cognee," and real API usage must be visibly real (logs, real graph state, real dashboard data).
- Do not overclaim in the README ("guaranteed accurate," "never hallucinates") — say "calibrated confidence," not "always correct."
- Keep the trust-scoring function simple and explainable over complex and opaque — a judge should be able to understand the four signals in one sentence each.
- Prefer working end-to-end (even if simple) over one polished component and three unfinished ones. A full pipeline demo beats a partial deep one.
- Update `## CURRENT STATUS` below after every session, before ending.
- **Stay scoped to this project folder only.** Never read, cd into, or modify any other project/repo on this machine (e.g. HireScript, TaskFlow, portfolio site). All demo data must be self-generated fixture files living inside this project's own directory.

---

## CURRENT STATUS

**Last updated:** July 2, 2026, Day 1 session (in progress, checkpoint 1 of N)

**Stage:** Day 1 — trust scoring done and verified against real data; consolidation and pruning not started yet.

**Day 1 progress so far:**
- Built `recall_service/trust_score.py`: four signals — `path_length_score` (from Cognee's real `topological_rank` field on CHUNKS results), `similarity_score` (rank-position proxy, since Cognee Cloud's CHUNKS endpoint returns `score: null` — no raw cosine score exposed in this API version, so we use ranked order instead), `recency_score` (exponential decay, half-life 30 days, computed from our own ingestion-time commit timestamps), `contradiction_penalty` (flat 0.6 penalty, driven by the `references` graph `ingest/memory_units.py` already extracts from revert/contradiction commit messages). Combined as `mean(path, similarity, recency) * (1 - contradiction_penalty)`, clipped to [0,1] — deliberately simple per §7.
- **Verified against real recall() data, not synthetic inputs** (`recall_service/verify_trust_score.py`, raw output in this session's transcript):
  - Revert case (`mu-e8c4a71`): scored 0.785 HIGH CONFIDENCE.
  - **Contradiction case — the key result:** query "Is ShiftLog's Postgres running locally via Docker?" returned the OLD memory `mu-a1f3c02` as the top semantic match (similarity=1.0) but it scored only **0.301 LOW** (contradiction_penalty=0.6), while the newer correct memory `mu-2c9e4f1` scored **0.801 HIGH**. This is the exact "don't blindly trust a stale-but-relevant memory" behavior the project is built around.
  - Clean control case (N+1 bug fix, uncontradicted): scored 0.834 HIGH, confirming contradiction — not just age — is what's driving the low score above.
- **Known limitation (being upfront, not overclaiming):** `path_length_score` returned 1.0 for every chunk in this run — `topological_rank` is 0 across the board in this small demo graph, so that signal isn't discriminating yet. It's a real API-sourced field, just not yet varying in a graph this size.
- Wrote `recall_service/tests/test_trust_score.py` — 19 real unit tests covering all four signals independently (path length, similarity, recency, contradiction) plus combine/label logic and one integration-style test. All 19 pass (`python3 -m pytest recall_service/tests/test_trust_score.py -v`).

**Next task:** Wire `consolidate/memify_job.py` (real `improve()`/`memify()` calls against `shiftlog_demo`), test specifically against the `mu-2c9e4f1` vs `mu-a1f3c02` contradiction pair to confirm Cognee's own consolidation actually merges/reweights them (as opposed to our trust-scoring layer just working around the contradiction at query time). Then `prune/forget_watcher.py` using the `mu-5f2b7c4` CSV-export deletion as the test case.

**Blockers:** None. Exact hackathon submission deadline time still needs confirming from the Schedule tab (low priority until Day 3).

**Notes for next session:**
- `recall_service/verify_trust_score.py` is the pattern to reuse for showing raw before/after output on the consolidation and pruning steps too — user wants raw output shown at each sub-step, not just a summary.
- Trust scoring signal weights (equal thirds + 0.6 contradiction penalty, 30-day recency half-life) are hardcoded constants at the top of `trust_score.py` — revisit if Day 2 demo tuning wants different behavior, but keep them simple/explainable per §7.

---

### Day 0 summary (COMPLETE)

**Done:**
- Scaffolded full repo structure per §5 (`ingest/`, `recall_service/`, `consolidate/`, `prune/`, `claude_code_bridge/`, `dashboard/`, `demo/`, `.env.example`), git initialized, `.venv` created, `requirements.txt` installed.
- **Scope change (user-directed):** demo data is NOT pulled from an external repo (HireScript/TaskFlow). Instead, `demo-data/` contains hand-authored, realistic synthetic data for a fictional project "ShiftLog": `commits.jsonl` (14 commits covering decisions, bug+fix pairs, a revert/rejected-approach, a later contradicting decision, and a file deletion) plus two session transcripts (`session_001_amnesia.md` showing the pain point, `session_002_with_memory.md` showing target behavior with HIGH/LOW confidence labels — this is aspirational reference for Day 2, not yet real bridge output).
- Built `ingest/git_reader.py` (parses `demo-data/commits.jsonl`) and `ingest/memory_units.py` (structures commits into MemoryUnit objects with provenance + cross-references). Verified via `python3 -m ingest.memory_units` — all 14 units parse correctly with references extracted (e.g. the revert and contradiction commits correctly link back to what they supersede).
- Installed real Cognee SDK (`cognee==1.2.2`) in `.venv`. User's Cognee Cloud tenant credentials (`COGNEE_API_KEY`, `COGNEE_API_BASE_URL`, `COGNEE_TENANT_ID`) added to `.env` (confirmed gitignored, not tracked).
- Built `ingest/remember_client.py` using `cognee.cli.api_client.CogneeApiClient` (the same HTTP client the `cognee` CLI uses in `--api-url` mode) to call the real hosted `/api/v1/remember` endpoint with `X-Api-Key` auth — this is the correct integration path for Cognee Cloud (the in-process `cognee.remember()` needs its own local LLM key for extraction; the cloud tenant does extraction server-side). Had to raise the client timeout from the 120s default to 600s — real server-side graph extraction took 13–43s per item and the default timeout truncated the run partway through on the first attempt.
- **Ran real ingestion: all 14/14 memory units successfully remembered** into Cognee Cloud dataset `shiftlog_demo` (`dataset_id: e9ff219e-cb70-5b18-8f4e-2bdf45aa6831`). Raw per-item responses (status, pipeline_run_id, items_processed, elapsed_seconds) captured in session transcript.
- **Ran real sanity `recall()` query** ("Why was Redis pub/sub reverted for shift-change notifications?") against `shiftlog_demo` — got back a correct `GRAPH_COMPLETION` answer pulled from the `mu-e8c4a71` revert memory unit, confirming the data is genuinely stored and queryable in the knowledge graph, not just accepted by the ingest endpoint.
- Added `ingest/recall_check.py` as a reusable sanity-check script.

**Next task:** Begin Day 1 — build `recall_service/trust_score.py` (path-length score, embedding similarity, recency decay, contradiction penalty → HIGH/MEDIUM/LOW label), with unit tests in `recall_service/tests/test_trust_score.py`. The `shiftlog_demo` dataset already has real contradiction (`mu-2c9e4f1` vs `mu-a1f3c02`) and revert (`mu-e8c4a71`) cases ingested, so the trust scorer can be tested against real recall() output, not synthetic scoring inputs.

**Blockers:** None. Exact hackathon submission deadline time still needs confirming from the Schedule tab (open item from the Day 0 checklist, low priority until Day 3).

**Notes for next session:**
- Demo data lives entirely inside `cognee-agent-memory/demo-data/` — do not read from any repo outside this project folder (explicit user instruction, saved to memory).
- Cognee Cloud integration goes through `CogneeApiClient` (`ingest/remember_client.py`'s `_client()` helper), not the in-process `cognee.remember()` — reuse that pattern for `recall_service/`, `consolidate/memify_job.py`, and `prune/forget_watcher.py` rather than re-deriving it.
- Real server round-trips are slow (10–45s per remember() call); when building `recall_service`'s FastAPI wrapper, do not assume sub-second latency in tests/demo timing.