"""Claude Code integration bridge — pre-task recall injection.

Wired as a Claude Code `UserPromptSubmit` hook (see .claude/settings.json
at the project root). Every time the user submits a prompt in a Claude
Code session on this project, Claude Code runs this script and pipes it
JSON on stdin: {"session_id", "transcript_path", "hook_event_name",
"prompt", "cwd", ...}. We:

  1. Pull the user's prompt text.
  2. Query recall_service (real Cognee CHUNKS recall, trust-scored) for
     that prompt directly — the plan's "touched file(s)" query is
     generalized to "the user's stated intent," since a fresh prompt
     often names a topic/file before any file is actually touched.
  3. Print JSON on stdout in Claude Code's expected hook-output shape:
     {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
       "additionalContext": "<trust-labeled memory block>"}}
     which Claude Code injects into the session as extra context before
     the agent responds — this is the actual "wow moment" the demo
     needs: a HIGH CONFIDENCE memory gets surfaced and trusted, a LOW
     CONFIDENCE one gets surfaced but flagged instead of silently
     believed.

Only memories scoring at or above a floor are injected at all — see
INJECT_FLOOR below. Below that floor we inject nothing (silence is
better than noise for a coding agent's context window).
"""

from __future__ import annotations

import json
import sys

from ingest.remember_client import DATASET_NAME, _client
from recall_service.trust_score import score_chunks

TOP_K = 5
INJECT_FLOOR = 0.2  # below this, don't bother injecting anything at all
MAX_INJECTED = 3


def query_recall(prompt_text: str, top_k: int = TOP_K):
    with _client() as client:
        chunks = client.recall(
            query=prompt_text,
            search_type="CHUNKS",
            datasets=[DATASET_NAME],
            top_k=top_k,
        )
    results = score_chunks(chunks, top_k=top_k)
    results.sort(key=lambda r: r.score, reverse=True)
    return results


def format_context_block(results) -> str:
    if not results:
        return ""
    above_floor = [r for r in results if r.score >= INJECT_FLOOR]
    top = above_floor[:MAX_INJECTED]
    # Contradicted memories are always worth surfacing even outside the
    # top-N cutoff — flagging a stale-but-relevant memory as LOW
    # confidence, rather than silently dropping it, is the whole point.
    contradicted = [r for r in above_floor if r.signals.contradiction_penalty > 0 and r not in top]
    injected = top + contradicted
    if not injected:
        return ""

    lines = ["## Relevant project memory (cognee-agent-memory)", ""]
    for r in injected:
        first_line = r.text.splitlines()[0] if r.text else ""
        lines.append(f"- **[{r.label}]** (score {r.score:.2f}, commit `{r.source_commit}`) {first_line}")
        signals = r.signals
        lines.append(
            f"  - signals: path={signals.path_length_score:.2f} "
            f"similarity={signals.similarity_score:.2f} "
            f"recency={signals.recency_score:.2f} "
            f"contradiction_penalty={signals.contradiction_penalty:.2f}"
        )
        if signals.contradiction_penalty > 0:
            lines.append("  - ⚠️ a newer memory contradicts this one — verify before relying on it.")
    return "\n".join(lines)


def main():
    raw_stdin = sys.stdin.read()
    try:
        payload = json.loads(raw_stdin) if raw_stdin.strip() else {}
    except json.JSONDecodeError:
        payload = {}

    prompt_text = payload.get("prompt", "")
    if not prompt_text:
        return  # nothing to query against, exit silently (valid no-op)

    results = query_recall(prompt_text)
    context_block = format_context_block(results)

    if context_block:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context_block,
            }
        }
        print(json.dumps(output))


if __name__ == "__main__":
    main()
