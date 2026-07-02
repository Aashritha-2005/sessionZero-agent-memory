# Demo video shot list

2–3 minutes, mapped to the beat sheet in `PROJECT_PLAN.md` §6. Every beat
below is tagged with what's actually backing it — **REAL/LIVE** (record
it happening for real, on camera, right now), **REAL/CAPTURED** (a real
result we already produced and can screen-record replaying, e.g. `cat`-ing
a log or re-running a script that hits the real API again), or
**ILLUSTRATIVE** (a scripted narrative device — must be framed as such
on screen, never implied to be a captured real session). Nothing in this
project should be presented as more real than it is.

---

### Beat 1 — Open on the pain (0:00–0:20)
**ILLUSTRATIVE.** Read from `demo-data/session_transcripts/session_001_amnesia.md`
on screen (or voice it over a terminal-style text animation) — the
"agent proposes Redis pub/sub again, already reverted" exchange.
**On-screen label required:** something like *"illustrative — this is
the failure mode we're solving, not a captured session."* This is a
narrative device to set up the problem, not a Cognee claim, so it's
fine to dramatize — just don't let it read as a real recording.

### Beat 2 — `remember()` ingesting real data, live (0:20–0:45)
**REAL/LIVE.** Don't replay old logs — ingest something new on camera
so the audience watches a real API call happen in real time. Script:
add one small new commit to `demo-data/commits.jsonl` before recording
(anything genuine, e.g. a follow-up bug fix), then run:
```
source .venv/bin/activate
python3 -m ingest.remember_one <new-hash>
```
Let the terminal output (`remembered mu-<hash> ... -> {'status': 'completed', ...}`)
sit on screen for a beat — that raw JSON *is* the proof.

### Beat 3 — HIGH confidence, live Claude Code session (0:45–1:15)
**REAL/LIVE, already confirmed working (2026-07-02).** Open a fresh
Claude Code session in this project directory and ask on camera:
*"Does ShiftLog use JWT for authentication?"* The `UserPromptSubmit`
hook fires for real, injects the trust-labeled context, and Claude
Code's response should cite the current session-cookie decision
(`mu-8c5f0d7`, HIGH) as authoritative. This exact query was already
live-tested and confirmed working — re-recording it is just capturing
what's already proven, not a fresh risk.

### Beat 4 — LOW confidence flagged, not blindly trusted (1:15–1:50)
**REAL/LIVE, same session as Beat 3 — this is the differentiator, dwell here.**
The same query/response from Beat 3 already surfaces *both* memories
in one shot: HIGH confidence `mu-8c5f0d7` (current) and LOW confidence
`mu-d5b6e13` (superseded JWT decision, ⚠️ contradiction warning) —
Claude Code's synthesized answer cites both commit hashes rather than
picking one blindly. Don't cut away after Beat 3; let this same
exchange play out and call out the LOW-confidence line explicitly.
This is the single most important moment in the video — the whole
"Best Use of Cognee" / "Creativity" pitch rests on this beat being
clearly visible.

### Beat 5 — Dashboard tour (1:50–2:20)
**REAL/LIVE.** Start both servers (`recall_service/api.py` on :8000,
static server on :5173 — exact restart commands are in this repo's
session history / README setup section), open
`http://127.0.0.1:5173/index.html`, and:
1. Scroll the timeline — point out the vertical rail, the strikethrough
   on the two forgotten entries (`mu-a1f3c02`, `mu-5f2b7c4`), the
   red-tinted LOW card with ⚠️ on `mu-d5b6e13`, and the "supersedes"
   label on the two contradiction entries.
2. Click a card open to show provenance (signals, source commit, data_id).
3. Optional finale, only if nothing else needs this data afterward:
   click "forget this" on a live entry and show it move to forgotten
   in real time — this is a real `forget()` call, not staged. Only do
   this as the *last* action recorded, since it permanently prunes
   that memory from the real dataset.

### Beat 6 — Four-API summary card (2:20–2:40)
**Text/graphic overlay, not a live action.** Show the Cognee API usage
table from `README.md` §"Cognee API usage" on screen — `remember()`,
`recall()`, `forget()` marked real/verified; `improve()`/`memify()`
marked honestly as SDK-only on Cognee Cloud with the `recall()`+`forget()`
reframing explained in one line. This honesty is itself worth a beat —
say it out loud, don't just caption it small.

---

## Recording checklist before hitting record
- [ ] `.env` has real credentials, both servers running (`curl localhost:8000/health`, `curl localhost:5173/index.html`)
- [ ] A fresh Claude Code session ready for Beats 3–4 (not this session — hooks may not hot-reload)
- [ ] Decide in advance whether Beat 5's live `forget()` click is happening — if yes, it's genuinely one-way for that memory
- [ ] Beat 1's illustrative framing is scripted/captioned, not left ambiguous
