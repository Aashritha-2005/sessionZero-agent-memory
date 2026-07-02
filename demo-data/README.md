# Demo Data

Synthetic-but-realistic data for a fictional project called **ShiftLog** (a
small shift-scheduling web app), generated for this hackathon demo. This is
**not** pulled from any real repository — it's hand-authored to look like a
real commit history so the ingestion pipeline has something meaningful to
`remember()`, and so the trust-scoring layer has genuine cases to reason
about: an architecture decision, a bug + fix, a rejected approach (revert),
a later decision that contradicts an earlier one, and a file deletion (for
`forget()`).

Files:
- `commits.jsonl` — one JSON object per line, each a synthetic commit
  (hash, timestamp, author, message, files changed, diff summary, type).
- `session_transcripts/session_001.md` — a synthetic Claude Code session
  transcript showing the "agent forgets and re-asks" pain point.

Types used in `commits.jsonl`:
- `decision` — an architecture decision
- `bug_fix` — a bug + its fix in the same commit
- `revert` — a rejected approach, explicitly reverted
- `contradiction` — a later decision that supersedes/contradicts an earlier one
- `deletion` — a file removal/rename (exercises `forget()`)
