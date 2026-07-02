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

**Last updated:** July 2, 2026 (project kickoff — plan created, no code written yet)

**Stage:** Day 0 — not yet started

**Next task:** Confirm Cognee Cloud setup and API keys, then scaffold repo structure per §5, then begin `ingest/git_reader.py`.

**Blockers:** None yet.

**Notes for next session:** None yet — this is the initial plan file.