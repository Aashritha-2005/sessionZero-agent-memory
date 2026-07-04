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

**Last updated:** July 5, 2026 (submission deadline day), Day 3 — Tier 3 in progress

**Stage:** Day 2 fully complete. Day 3: demo shot list, README accuracy pass, §0.1 compliance check, three additive scope extensions, live deployment (Tier 1), Tier 2 (1 of 2 landed), and now **Tier 3** — explicitly re-opened by the user on submission deadline day after I flagged that these items were originally scoped "do not attempt" for exactly the reasons that still apply. User explicitly confirmed proceeding anyway, understanding the risk. Tagged `pre-tier3-pass` at commit `ada4947` as a clean rollback point before starting, same discipline as the earlier hardening-pass attempt.

**Tier 3 item 1 (real statistical calibration) — attempted honestly, real limitation confirmed, not glossed over:** Rebuilt `recall_service/calibration.py` (read-only, ground truth from live dataset state — forgotten/superseded status, no dataset mutation) and ran it for real: 15 queries, 182 (query, result) samples, ground truth clean (12 valid / 3 stale, matching exactly what's expected — no repeat of the earlier `c02fa88` anomaly). Real bucket accuracy: `[0.2,0.4): 14 samples, 0% acc`, `[0.4,0.6): 20 samples, 100%`, `[0.6,0.8): 109 samples, 100%`, `[0.8,1.0): 39 samples, 100%`. **Critical caveat, stated plainly rather than hidden:** only one memory unit (`d5b6e13`) is ever stale-and-recallable in this dataset (the other two stale cases, `a1f3c02`/`5f2b7c4`, are forgotten and never appear in any recall results at all) — so the 14 low-bucket samples are the same single memory recurring across 14 different queries, not 14 independent examples of staleness. One data point cannot demonstrate a calibration curve no matter how many queries you run against it. This confirms, with real numbers this time, exactly what the task's own reasoning predicted: real statistical calibration isn't achievable with this dataset's size, regardless of how many queries are thrown at it. No claim of "calibration achieved" is being made anywhere in README/docs.

**Tier 3 item 2 (fixing path_length_score to discriminate) — declined, not forced.** Confirmed this requires "a much larger, structurally varied graph" per the task's own reasoning, and there's no honest way to get one without either (a) bulk-ingesting real data into `shiftlog_demo` — violating the standing "don't touch the demo dataset's contents" rule carried from Tier 1/2 — or (b) building and validating a separate large graph in time that isn't available. Declined to fabricate a fix. `trust_score.py` was not touched for this item. Remains exactly the documented, disclosed limitation it already was.

**Tier 3 item 3 (interactive live-query trust-signal visualization) — scoped down to a safe version, not the full ask.** The full version (new interactive live-query feature) was explicitly flagged as too much new-surface-area risk this close to submission, and that reasoning still holds. Built the safest possible version instead: the 4 trust signals were already computed and already displayed as plain numeric text in every card's provenance panel — replaced that with a small pure-CSS horizontal bar per signal (`signalBar()` in `dashboard/index.html`), using the exact same already-fetched values. No new endpoint, no new fetch call, no new interactive state beyond the existing click-to-expand provenance toggle. Verified: JS syntax valid, full functional check confirms every pre-existing value (timeline count, forgotten count, `d5b6e13`/`8c5f0d7` labels and signals, recall HIGH/LOW, summaries) is byte-identical to before this change, 28/28 tests pass, ruff clean.

**Tier 2 item 7 — DONE:** `GET /summaries` added to `recall_service/api.py`, using Cognee's real `SUMMARIES` search type (confirmed real via Day 1 exploration, tested live against the real dataset — genuinely different output shape from `CHUNKS`/`GRAPH_COMPLETION`: condensed bullet-point recaps). Deliberately not trust-scored and does not touch `trust_score.py` — used a small locally-scoped regex in `api.py` instead of reusing `trust_score.py`'s `extract_commit_hash()` (which expects our own ingestion format, not Cognee's free-form summary prose). Wired into the dashboard's Search tab as a new "Summaries" button with its own (unscored) card rendering. Verified: 28/28 tests still pass, ruff clean, full functional check confirms zero regression to existing timeline/recall/forget behavior.

**Tier 2 item 6 — ABANDONED, real friction, documented honestly:** attempted a local, disconnected Cognee instance (own dataset `local_improve_demo_scratch`, never touching `shiftlog_demo`) to demonstrate real `improve()`/`memify()` on the SDK surface where they're actually supported. User provided a Groq API key. Hit two independent, genuine configuration dead-ends in sequence, each requiring real research to diagnose (not guessed past):
  1. Cognee's `LLMProvider` enum doesn't include `"groq"` at all (`ValueError: 'groq' is not a valid LLMProvider`) — real providers are `openai/ollama/anthropic/custom/gemini/mistral/azure/bedrock/llama_cpp`. Worked around this using `LLM_PROVIDER=custom` + `LLM_ENDPOINT=https://api.groq.com/openai/v1` (Groq's real OpenAI-compatible endpoint).
  2. After fixing that, hit a second, independent gap: Cognee's embedding config defaults to OpenAI (`embedding_provider: openai`) regardless of the LLM provider setting, and Groq doesn't offer an embeddings API at all — the embedding connection test then timed out.
  Two genuine, independent environment-config gaps in a row is exactly the "any friction → abandon" case the task itself specified. Stopped rather than chasing a third free embedding provider. Cleaned up fully: deleted the non-working `consolidate/local_improve_demo.py` script (never committed, so no repo trace), removed the experimental `LLM_*` lines from `.env` (restored to just the Cognee + Railway credentials it had before), confirmed the real Cloud tenant client and deployed URL are both unaffected (28/28 tests pass, deployed `/health` still 200).
  `improve()`/`memify()` remain exactly what they were before this attempt: documented in the README as SDK-only on Cognee Cloud, with the reframed `consolidate_contradictions()` (reference-graph + real `forget()`) as the real, working consolidation path. Nothing about that story changed — this attempt neither strengthened nor weakened it, it just didn't land.

**🔗 LIVE DEPLOYMENT:** https://web-production-67f7f.up.railway.app — real Cognee Cloud dataset (`shiftlog_demo`), deployed on Railway. Verified for real:
- `GET /` → 200, serves the SessionZero dashboard
- `GET /health` → 200, real Cognee backend health (postgres/pgvector/graph_db all healthy)
- `GET /timeline` → 200, count 15, `a1f3c02`/`5f2b7c4` correctly forgotten
- `GET /recall?query=Does ShiftLog use JWT for authentication?` → 200, reproduces the signature result exactly: `8c5f0d7` HIGH 0.975, `d5b6e13` LOW 0.293 with contradiction penalty
- `POST /forget` confirmed present in the deployed OpenAPI spec, not invoked against the live deployment (would permanently prune real demo data needed for the recording) — its logic is identical to what's already verified locally and in earlier sessions

**Deployment path taken (documented honestly, since it had real friction, not a smooth one-shot):**
- Initial attempt used a Railway *project token* (`RAILWAY_TOKEN`) non-interactively via CLI — failed consistently across `whoami`/`status`/`link`/`up` with "Unauthorized"/"Not signed in" despite the token loading correctly and matching Railway's own current docs exactly. Diagnosed thoroughly (confirmed shell env, confirmed docs, retried after project+service existed) before concluding it was a genuine CLI/token issue, not a mistake on our side.
- Pivoted to connecting GitHub directly via Railway's web dashboard instead of fighting the CLI further — this is what actually worked.
- Hit one more real snag: the first Railway project/service ("splendid-encouragement" in "giving-delight") had its Source connected to a *different*-looking repo name (`sessionZero-agent-memory`) that turned out to be our own repo after a GitHub auto-rename (`cognee-agent-memory` → `sessionZero-agent-memory`, confirmed via matching commit SHA `a34286c`) — but that service never actually had an active deployment triggered, so `/health` kept 404ing with Railway's own edge fallback error. Rather than keep debugging that project, the user restarted clean as a new Railway project ("cozy-kindness", service "web"), reconnected the (correctly-named-now) GitHub repo, and that deployed successfully on the first real build.
- Local git remote updated to `github.com/Aashritha-2005/sessionZero-agent-memory` to match the renamed repo.

**Additive scope extensions (user-directed, explicitly scoped to not touch `trust_score.py`, `bridge.py`, the dashboard, or any verified Cognee integration code):**

1. **Generalized ingestion** — `ingest/git_reader.py` gained `read_commits_from_repo()`, parsing a *real* repo's actual `git log` output (subprocess-based: `git log`, `git diff-tree`, `git show --shortstat`) into the same `Commit`/`MemoryUnit` shape as the demo-data path. `read_commits()`'s default behavior is completely unchanged (verified: identical output before/after, all 24 pre-existing tests still passed). Added `_classify_message()` — a conservative heuristic (detects `revert`/`deletion`/`bug_fix` from message keywords, falls back to a generic `"commit"` kind rather than mislabeling everything as `"decision"`, since real commits don't carry our demo-data's explicit type field). **Tested against a real external repo**: cloned `jonschlinkert/is-number` (MIT licensed, 62 real commits) to `/tmp`, parsed it for real, fed the output straight into unmodified `memory_units.py`, and deleted the clone afterward (did not touch any other local project folder, per earlier scope-boundary instruction). Verified real classifications: `"Remove dependency on kind-of"` → `deletion`, `"fix for booleans and date objects"` → `bug_fix`, with real `files`/`diff_summary` from actual git output.

2. **Second agent bridge (`claude_code_bridge/codex_bridge.py`)** — before writing any code, looked up Codex's *real* hook contract by reading Cognee's own shipped Codex plugin source on GitHub (`topoteretes/cognee-integrations`, `integrations/codex/plugins/cognee/hooks.json` and `scripts/session-context-lookup.py`) rather than guessing or assuming Claude Code's format would transfer. **Finding: Codex's `UserPromptSubmit` hook contract is byte-identical to Claude Code's** (same stdin `{"prompt": ...}`, same stdout `{"hookSpecificOutput": {"hookEventName", "additionalContext"}}`) — confirmed from real source, not assumed. `codex_bridge.py` implements this contract and calls `recall_service/api.py`'s `/recall` endpoint over real HTTP (stdlib `urllib`, no new dependency, no import from `bridge.py`) — proving a second, genuinely independent client can use the same service. **Verified live against the running `recall_service`**: real HTTP call, correct HIGH (`mu-8c5f0d7`, 0.99) and LOW (`mu-d5b6e13`, 0.28, contradiction-flagged) results for the same JWT query used in the Claude Code live test. Edge cases (empty prompt, missing field, unreachable server) all verified to fail silently on stdout with exit 0, per hook-safety requirements. **Honesty disclosure (same standard as `improve()`/`memify()`): NOT tested inside an actual Codex CLI session** — Codex isn't installed here and the full `codex plugin marketplace add ...` install flow was out of scope for the time remaining. This is structurally-verified-against-real-source + HTTP-tested, not live-Codex-confirmed. Documented as such in the file's own docstring, not just here. 4 new unit tests in `claude_code_bridge/tests/test_codex_bridge.py`, all passing.

3. **README "Beyond Claude Code" section** — states the architectural claim (recall_service/api.py is the agent-agnostic core; the Claude Code bridge is one integration on top) and backs it with `codex_bridge.py` as evidence rather than leaving it as an assertion, including the same honest live-vs-structural caveat as above.

**Verification after all three additions**: `python3 -m pytest recall_service/tests/ claude_code_bridge/tests/ -q` → 28/28 passing (24 pre-existing + 4 new). `git diff` confirms zero changes to `recall_service/trust_score.py`, `claude_code_bridge/bridge.py`, `dashboard/`, `recall_service/api.py`, `consolidate/`, or `prune/` — only additive new files plus the generalized (but default-unchanged) `git_reader.py`.

**Day 3 progress — demo shot list + README accuracy pass + compliance check:**

1. **`demo/demo_script.md`** — shot list mapped to the §6 beat sheet. Each beat explicitly tagged REAL/LIVE, REAL/CAPTURED, or ILLUSTRATIVE, so the recording never presents something as more real than it is (e.g. Beat 1's "agent forgets" cold-open is an illustrative dramatization of `demo-data/session_transcripts/session_001_amnesia.md`, not a captured session, and must be labeled as such on screen). Beats 3–4 (HIGH + LOW confidence in one live Claude Code exchange) are now backed by the actual confirmed live test, not just a plan.

2. **README accuracy pass — two real mischaracterizations found and fixed, not just a re-read:**
   - `consolidate_contradictions()` was described as "recall()+forget()-based" in both README and this file. **Actually false** — the function itself never calls `recall()`; it uses the reference graph from `memory_units.py` + a dataset listing (`dataset_index.py`) + real `forget()`. `recall()` is only used in the separate `verify_consolidation.py` script, for before/after proof, not inside the consolidation logic. Fixed in README's architecture diagram, component table, and API usage table, and in this file's Day 1 log entries.
   - `recall_service/api.py`'s `/timeline` endpoint was implied to use `recall()` (grouped together with `/recall` in README's API usage table). **Actually false** — `/timeline` lists dataset data directly and never calls `client.recall()`. Fixed with an explicit callout in the README table.
   - Also added two disclosures that were true but missing from README (present in this file but not carried over): the `path_length_score` known-limitation (topological_rank=0 for every result in this small graph), and a placeholder demo-video link (required by §6 checklist, was entirely absent).
   - Re-ran `python3 -m pytest recall_service/tests/ claude_code_bridge/tests/ -q` after all edits — still 24/24 passing, confirming the fixes were docs-only.

3. **§0.1 rule-compliance checklist — run against actual repo state, not assumed:**
   - Rule 1 (Cognee as core mechanism): ✅ — entire project is built on real `remember`/`recall`/`forget` calls against Cognee Cloud; `improve`/`memify` gap is disclosed, not hidden.
   - Rule 2 (no work before June 29): ✅ — checked via `git log` (all 16 commits dated 2026-07-02, first commit `55f79c3` is the actual project start, no gaps or backdating) and via `find ... -exec stat` (all 38 tracked files have a 2026-07-02 mtime, nothing pre-existing).
   - Rule 3 (AI disclosure): ✅ — present in README, and accurate: only claims Claude Code (we never used Codex, so the README correctly doesn't claim it).
   - Rule 4 (no Cognee repo PR spam): ✅ N/A — Open Source Track not attempted, zero interaction with Cognee's GitHub repo.
   - Rule 5 (original work on allowed third-party tools): ✅ — checked `requirements.txt` (`cognee`, `fastapi`, `uvicorn`, `python-dotenv`, `pytest`, all standard pip packages, no vendored/copied code).
   - Rule 6 (no harassment): ✅ N/A, solo team.
   - Rule 7 (IP): ✅, solo team, no conflict.
   - Rule 8 (job-interview framing): ✅ N/A, not applicable to this submission's messaging.
   - Also checked: `.env` confirmed not tracked (`git ls-files` clean), no hardcoded API keys/secrets anywhere in tracked files (`git grep` for key-shaped strings returned nothing).

**Tier 1 pre-submission deployment pass — all done, in order:**

1. **Backend + dashboard deployed** — see "LIVE DEPLOYMENT" callout above. One Railway service serves both (`recall_service/api.py`'s `GET /` now returns `dashboard/index.html` via `FileResponse`); `dashboard/index.html`'s `API_BASE` is environment-aware (relative/same-origin when served by the backend, falls back to `localhost:8000` only for the separate-port local dev flow) — verified functionally identical to before at each step.
2. **CI pipeline + linting** — `.github/workflows/ci.yml` runs `ruff check .` + the full test suite on every push. Fixed all 10 real lint findings (3 unsorted-import blocks, 4 ambiguous `l` variable names, 3 over-length lines) — 0 remaining. Confirmed the test suite needs zero Cognee credentials to pass (pure unit tests), so CI needs no secrets. Both pushes to `master` are green: runs `28711483320` and `28711570524`.
3. **Dependency pinning** — `requirements.txt` pinned to exact installed versions (`cognee==1.2.2`, `fastapi==0.139.0`, `uvicorn[standard]==0.49.0`, `python-dotenv==1.2.2`, `pytest==9.1.1`); verified a completely fresh venv installs cleanly and all 28 tests still pass. `requirements-dev.txt` adds pinned `ruff==0.15.20` for CI.
4. **README final polish** — table of contents added; ASCII architecture diagram replaced with a real hand-written SVG (`docs/architecture.svg`, embedded as an image, not a chat-only widget); live deployment URL added at the top, above the fold; demo video placeholder retained (still pending recording); also disclosed the `path_length_score` dead-weight and unknown-scale-behavior limitations that came up in conversation, in addition to the pre-existing unexplained-disappearance disclosure.

**Repo rename note:** partway through deployment, GitHub reported our repo had moved to `Aashritha-2005/sessionZero-agent-memory` (auto-renamed, likely by the Railway GitHub App's naming, confirmed to be the same repo via matching commit SHA `a34286c`). Local `origin` remote updated to match. The live Railway deployment is on a separate fresh project ("cozy-kindness"/"web") after the first project's service ("giving-delight"/"splendid-encouragement") never got an active deployment triggered — that first service can be deleted or left idle, it's not doing anything.

**Next task:** Record the demo video per `demo/demo_script.md` (real live deployed URL, plus the new `/summaries` search and the signal-bar provenance view are both good optional beats now), confirm the exact submission deadline time from the hackathon Schedule tab (still unconfirmed — do not assume end-of-day July 5, and today IS that day), add the real video link to README, then final submit with buffer before the deadline.

**Blockers:** None. Demo video recording and deadline-time confirmation are the two remaining substantive tasks, and this is genuinely the last safe moment to do them — no more scope should be added today. Tier 1 fully done. Tier 2: item 7 done, item 6 honestly abandoned after real friction. Tier 3: item 1 (calibration) attempted honestly with a clear real-limitation finding, item 2 (path_length_score) correctly declined as not safely achievable, item 3 (visualization) delivered as a deliberately scoped-down, low-risk version rather than the full flagged-risky feature. Every Tier 3 outcome was reported honestly rather than forced or glossed over.

---

### Day 2 summary (COMPLETE)

**Day 2 closeout — live hook test PASSED (user-confirmed 2026-07-02):** the last open item from Day 2 — a human watching the `UserPromptSubmit` hook fire inside an actual running Claude Code UI session, as opposed to invoking it directly with the same stdin/stdout contract — is now done. In a fresh Claude Code session on this project, the hook fired for real and injected both the LOW-confidence superseded JWT memory (`mu-d5b6e13`) and the HIGH-confidence current session-cookie memory (`mu-8c5f0d7`); Claude Code synthesized the correct current-state answer citing both commit hashes rather than picking one blindly. This is the exact "wow moment" the plan's §6 demo beat sheet calls for (beat 3 and 4 — HIGH correctly trusted, LOW correctly flagged instead of blindly trusted), now proven live end-to-end, not just via direct script invocation. No code changes were needed — the hook worked as built.

**Dashboard visual polish (since last update):** `dashboard/index.html` received a presentation-only pass per user request — vertical timeline rail with colored marker dots, strikethrough on forgotten titles, red-tinted cards + ⚠️ icon on LOW-confidence entries, "supersedes &lt;hash&gt;" labels on the two contradiction-kind entries (using the `references` field already returned by `/timeline`), tighter title/metadata type hierarchy. Verified via a live `/timeline` fetch that all data (contradiction references, LOW/forgotten status/counts) is unchanged — markup/CSS only, no logic touched.

**Day 2 sub-step 3 (README) — done:**
- `README.md` drafted: problem statement, ASCII architecture diagram, component table, "why synthetic demo data" explainer, the full Cognee API usage table (§3) — including the honest `improve()`/`memify()` limitation writeup as a called-out strength rather than something downplayed — trust-scoring explainer with the real verified JWT example (0.99 HIGH vs 0.28 LOW), setup instructions, and the AI Assistance Disclosure (§6).
- Not yet done: demo video/GIF link (Day 3), blog post (optional stretch), social posts (optional stretch).

**Day 2 sub-step 2 (dashboard) — done:**
- Extended `recall_service/api.py` with `GET /timeline` (every memory unit, chronological, with a query-independent baseline trust score — similarity is neutral/1.0 since there's no active query outside a search — and live-vs-forgotten status) and `POST /forget` (manual prune by commit hash, reusing the exact `dataset_index` resolution already proven in Day 1's `forget_watcher.py`).
- `dashboard/index.html` — single-page vanilla HTML/JS, no build step. Chronological timeline, HIGH/MEDIUM/LOW/forgotten color-coding, click-to-expand provenance (signals, files, source commit, data_id, superseded-by), and a "forget this" button.
- **Verified `/timeline` against real data**: `mu-a1f3c02` and `mu-5f2b7c4` (both pruned for real in Day 1) correctly show `status: "forgotten"`; all 13 other entries show `status: "live"`. Exact match to what Day 1's real `forget()` calls did.
- **Verified the dashboard's actual fetch/render logic end-to-end**, not just the API in isolation: extracted `index.html`'s JS and ran it under Node against the live FastAPI server (`http://127.0.0.1:8000`), executing the same `levelOf()`/rendering logic the browser would. Real result: `timeline count: 15, forgotten: 2, HIGH: 13, LOW: 2`; a live `/recall` query returned both a HIGH and a LOW confidence result as expected.
- **Known gap, disclosed**: no actual pixel screenshot was taken — the Chrome extension isn't connected in this sandbox and the `preview_start` tool hit an unrelated sandbox permission error (`getcwd: cannot access parent directories`). Per user decision (2026-07-02), the non-visual verification above was accepted as sufficient for now; user will open `dashboard/index.html` themselves in a real browser to visually confirm. Did not trigger a real `/forget` call from the dashboard button in testing (would prune more demo data still needed for the video) — that code path is identical to the twice-already-proven `forget_watcher.py` logic, so this is a coverage note, not an open risk.

**Day 2 sub-step 1 (bridge) — still open item:** a genuine interactive live test where a human watches the `UserPromptSubmit` hook fire inside a running Claude Code UI session hasn't happened yet (verified so far by invoking the hook script directly with the same stdin/stdout JSON contract, which is a strong but not identical proof). `.claude/settings.json` targets this project directory, so a fresh Claude Code session here should trigger it for real — worth a user confirmation when convenient, not blocking.

**Day 2 progress so far:**

- **Fresh demo fixture added**: since Day 1's `forget()` demo already pruned the original Postgres/Docker contradiction (`mu-a1f3c02`) from the graph, there was no live LOW-confidence case left to demo. Added a new commit `8c5f0d7` ("Move auth from JWT to server-side session cookies", kind=`contradiction`, supersedes `d5b6e13`) to `demo-data/commits.jsonl` and ingested it for real via a new `ingest/remember_one.py` (single-commit ingest helper). Verified via real `recall()`: `mu-8c5f0d7` scores **0.99 HIGH**, the old `mu-d5b6e13` (JWT decision) scores **0.28 LOW**.
- **Bug found and fixed while adding the fixture**: `ingest/memory_units.py`'s reference-extraction regex matched *any* 7-hex-char token in a commit message, not just genuine supersession references — an incidental mention like "not repeating the e8c4a71 mistake" would have been misread as a real contradiction reference. Tightened the regex to only match hashes introduced by explicit phrases ("reverts commit X", "Supersedes ... X", "changed from X"). Verified via `python3 -m ingest.memory_units` that all real references (including the new one) still extract correctly with no false positives, and all 19 existing trust-score tests still pass.
- **`recall_service/api.py`** — FastAPI `/recall` (real trust-scored CHUNKS recall) and `/health`. Verified via `TestClient`: real 200 response, correct HIGH-confidence result for `mu-8c5f0d7` (raw output captured this session).
- **`claude_code_bridge/bridge.py`** — implements Claude Code's real `UserPromptSubmit` hook contract (reads hook JSON on stdin, prints `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}` on stdout). Wired into `.claude/settings.json` (tracked in git — `.gitignore` narrowed from blanket `.claude/` to just the harness's own lock files, so this real hook config ships with the repo).
  - **Verified by invoking it exactly as Claude Code's hook runtime would** (same stdin/stdout JSON contract), three real queries:
    - "Does ShiftLog use JWT for authentication?" → HIGH confidence `mu-8c5f0d7` (0.99) AND LOW confidence `mu-d5b6e13` (0.28, ⚠️ contradiction warning) both surfaced in the same response.
    - "Should we use Redis pub/sub for real-time shift notifications?" → HIGH confidence `mu-e8c4a71` (revert) surfaced correctly.
  - **Bug found and fixed**: the LOW-confidence contradicted memory was initially getting cut off by the top-3 `MAX_INJECTED` limit (it ranked 4th by raw score). Fixed `format_context_block()` so contradicted memories always surface regardless of rank — flagging them is the entire point of the tool, so silently dropping one because it ranked 4th would defeat the purpose. Re-verified after the fix: both HIGH and LOW cases now appear together.
  - `claude_code_bridge/tests/test_bridge.py` — 5 new unit tests covering the floor cutoff, top-N inclusion, and the always-surface-contradictions behavior. 24/24 tests pass project-wide (`python3 -m pytest claude_code_bridge/tests/ recall_service/tests/ -q`).
  - **Not yet done**: a genuine interactive live test where a human watches the hook fire inside an actual running Claude Code UI session (as opposed to invoking the hook script directly with the same stdin/stdout contract, which is what's verified so far). Since `.claude/settings.json` now targets this very project directory, the next real prompt in a live Claude Code session here should trigger it — worth having the user confirm this fires as expected in practice, since hook settings may only be read at session start rather than hot-reloaded.

**Next task:** Day 3 (§4) in progress — demo video shot list being planned against what's actually verified (not aspirational), README final accuracy pass, full §0.1 rule-compliance checklist, then confirm exact submission deadline time from the Schedule tab, then submit with buffer.

**Blockers:** None. Both items carried from Day 2 (live hook confirmation, visual dashboard check) are now resolved — see closeout note above.

---

### Day 1 summary (COMPLETE)

**Stage:** Day 1 done. Trust scoring, consolidation (reframed), and pruning are all built and verified against real Cognee Cloud data.

**Day 1 summary:**

1. **`recall_service/trust_score.py`** — four signals: `path_length_score` (Cognee's real `topological_rank` field), `similarity_score` (rank-position proxy — Cognee Cloud's CHUNKS endpoint returns `score: null`, no raw cosine exposed in this API version), `recency_score` (exponential decay, 30-day half-life, from our own ingestion-time commit timestamps), `contradiction_penalty` (flat 0.6, driven by the reference graph `ingest/memory_units.py` extracts from revert/contradiction commit messages). Combined as `mean(path, similarity, recency) * (1 - contradiction_penalty)`, clipped [0,1].
   - **Verified against real recall() data**: contradiction case — old, contradicted memory `mu-a1f3c02` was the top semantic match (similarity=1.0) but scored only **0.301 LOW**; the correct newer memory `mu-2c9e4f1` scored **0.801 HIGH**. Clean control (uncontradicted N+1 bug fix) scored 0.834 HIGH, isolating contradiction (not age) as the driver.
   - Known limitation, disclosed not hidden: `topological_rank` is 0 for every chunk in this small demo graph, so `path_length_score` isn't discriminating yet — real API field, just not varying at this graph size.
   - `recall_service/tests/test_trust_score.py`: 19 real unit tests, all passing, covering all four signals independently plus combine/label logic.

2. **`consolidate/memify_job.py` — reframed from improve()/memify() to reference-graph analysis + real forget(), verified with recall().** Confirmed two independent ways that `improve()`/`memify()` are SDK-only, not hosted HTTP endpoints on Cognee Cloud: (a) tenant's live `GET /openapi.json` lists only `add/add_text/cognify/remember/remember-entry/recall/forget` plus dataset/session/permission/schema management — no improve/memify; (b) Cognee's own docs (docs.cognee.ai/api-reference) confirm improve()/memify() "cannot be sent over HTTP because they require live Python objects." This is architectural, not an auth/version gap — confirmed via a 5-minute doc check per user's explicit direction, then stopped investigating.
   - **Reframed approach**: `consolidate_contradictions()` uses our own contradiction index (from `memory_units.py` reference extraction) + a new `ingest/dataset_index.py` (resolves real Cognee `data_id`s by listing dataset data and matching embedded commit hashes in each item's raw text) to call real `forget(data_id=...)` on superseded memories.
   - **Verified real before/after**: `mu-a1f3c02` present in `recall()` results before, `forget()` returned `{"status": "success"}`, **confirmed absent after** — a genuine graph mutation, not a claim.

3. **`prune/forget_watcher.py`** — detects `demo-data/commits.jsonl` commits of kind `deletion`, resolves their real `data_id`, calls real `forget()`.
   - **Verified real before/after** on the `mu-5f2b7c4` CSV-export-removal case: present in `recall()` results before, `forget(data_id="12642103-...")` returned `{"status": "success"}`, **confirmed absent after**.

**All four Cognee lifecycle APIs are now exercised for real**: `remember()` (14 memories), `recall()` (trust-scored queries across multiple cases), `forget()` (contradiction pruning + file-deletion pruning, both verified with before/after diffs). `improve()`/`memify()` are implemented against the SDK surface but not callable against the hosted tenant — documented honestly, not faked, with the reframed consolidation (reference-graph analysis + real `forget()`, verified via `recall()`) serving the same lifecycle purpose (merge/prune stale knowledge) within what's actually real. Note: `consolidate_contradictions()` itself does not call `recall()` — it resolves superseded memories via the reference graph + a dataset listing, then calls `forget()`; `recall()` is used only in the separate before/after verification script to prove the pruning worked.

**Next task:** Begin Day 2 (§4) — wire `claude_code_bridge/bridge.py` using Cognee's official Claude Code integration guide; live-test a real Claude Code session recalling trust-scored context; build the dashboard (timeline, confidence color-coding, provenance drill-down, manual forget button); start drafting README (including the honest improve/memify note and AI Assistance Disclosure).

**Blockers:** None. Exact hackathon submission deadline time still needs confirming from the Schedule tab (low priority until Day 3).

**Notes for next session:**
- `ingest/dataset_index.py` (commit hash → real Cognee data_id resolution) is the reusable piece for anything that needs to target a specific memory for forget() — the dashboard's manual "forget this" button should reuse it rather than re-deriving.
- `recall_service/verify_trust_score.py`, `consolidate/verify_consolidation.py`, `prune/verify_forget.py` are the before/after raw-output verification pattern used throughout — keep using it for Day 2's live Claude Code integration test too.
- README's Cognee API usage table (§3) must state plainly: `remember()`/`recall()`/`forget()` are deeply and genuinely exercised; `improve()`/`memify()` are SDK-only on Cognee Cloud (confirmed via docs + live OpenAPI spec) and are not called against the hosted tenant — the reframed `consolidate_contradictions()` (reference-graph analysis + real `forget()`, no `recall()` call inside the function itself) is what actually runs for consolidation. Do not imply improve()/memify() executed successfully, and do not imply `recall()` is part of the consolidation logic — it's the separate verification step.
- The `CogneeApiClient.datasets_list()` method in the installed `cognee` package has a bug — it calls `/api/v1/datasets` without a trailing slash and gets an empty body back. `ingest/dataset_index.py` works around this by hitting `/api/v1/datasets/` directly via the client's underlying httpx client.

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