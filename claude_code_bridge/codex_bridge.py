"""Codex integration bridge — proves recall_service/api.py is agent-agnostic.

HONESTY NOTE (read before trusting this file): this hook's wire contract
(stdin JSON, stdout `hookSpecificOutput` shape) is copied from Cognee's
real, shipped Codex plugin — verified by reading the actual source at
github.com/topoteretes/cognee-integrations, specifically:
  integrations/codex/plugins/cognee/hooks.json
  integrations/codex/plugins/cognee/scripts/session-context-lookup.py
Codex's `UserPromptSubmit` hook turns out to use the *exact same* JSON
shape as Claude Code's (stdin: `{"prompt": "...", ...}`, stdout:
`{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
"additionalContext": "..."}}`) — this was confirmed by reading Cognee's
real plugin source, not assumed by analogy.

What IS verified: this script's stdin/stdout contract matches Codex's
real hook wire format (structurally confirmed against real source), and
it makes a real HTTP call to this project's own `recall_service/api.py`
`/recall` endpoint (not a mock, not duplicated logic — the same live
service `claude_code_bridge/bridge.py` and the dashboard both use).

What is NOT verified: this has not been run inside an actual Codex CLI
session (Codex isn't installed in this environment, and wiring the full
`codex plugin marketplace add ...` flow was out of scope for the time
left before the hackathon deadline). Treat this as a structurally-correct,
HTTP-tested stub proving the underlying claim — "any agent that can call
an HTTP endpoint can use the same trust-scored recall" — not as a
live-in-Codex-confirmed integration the way claude_code_bridge/bridge.py
now is for Claude Code.

Deliberately does not import anything from bridge.py — this file talks to
recall_service/api.py purely over HTTP, exactly as a real separate agent
process would, rather than reusing in-process Python objects.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

RECALL_SERVICE_URL = os.environ.get("RECALL_SERVICE_URL", "http://127.0.0.1:8000")
TOP_K = 5
INJECT_FLOOR = 0.2
MAX_INJECTED = 3


def call_recall_service(prompt_text: str, top_k: int = TOP_K) -> list[dict]:
    """Real HTTP call to this project's recall_service/api.py /recall
    endpoint — the same agent-agnostic service the Claude Code bridge and
    dashboard use. No direct Cognee client import here on purpose."""
    query = urllib.parse.urlencode({"query": prompt_text, "top_k": top_k})
    url = f"{RECALL_SERVICE_URL}/recall?{query}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        body = json.loads(resp.read())
    return body.get("results", [])


def format_context_block(results: list[dict]) -> str:
    """Same shaping logic as bridge.py's format_context_block, but
    operating on the /recall endpoint's plain-dict JSON response instead
    of in-process TrustResult objects — this file never imports from
    bridge.py, it only talks to the shared HTTP service."""
    if not results:
        return ""
    above_floor = [r for r in results if r["score"] >= INJECT_FLOOR]
    top = above_floor[:MAX_INJECTED]
    contradicted = [r for r in above_floor if r["signals"]["contradiction_penalty"] > 0 and r not in top]
    injected = top + contradicted
    if not injected:
        return ""

    lines = ["## Relevant project memory (cognee-agent-memory, via Codex bridge)", ""]
    for r in injected:
        first_line = r["text"].splitlines()[0] if r.get("text") else ""
        lines.append(
            f"- **[{r['label']}]** (score {r['score']:.2f}, commit `{r['source_commit']}`) {first_line}"
        )
        if r["signals"]["contradiction_penalty"] > 0:
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
        return

    try:
        results = call_recall_service(prompt_text)
    except Exception as exc:
        # Fail silently on stdout (a broken hook must never break the
        # host agent's turn) but say why on stderr for debugging.
        print(f"codex_bridge: recall_service call failed: {exc}", file=sys.stderr)
        return

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
