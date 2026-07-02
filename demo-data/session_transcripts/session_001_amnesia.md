# Session 001 — "the agent forgets" (baseline, no memory layer)

**Repo:** ShiftLog (synthetic demo project, see `../commits.jsonl`)
**Date:** 2026-06-28
**Context:** No memory layer attached. This transcript is the "pain point"
footage for demo beat #1 — the agent has no idea a Redis pub/sub approach
was already tried and reverted three weeks earlier (commit `e8c4a71`).

---

**User:** The shift calendar feels laggy when another manager updates a
shift — can you make updates show up in real time instead of the 10s poll?

**Assistant:** Sure — I'd recommend using Redis pub/sub for this. We can
have the backend publish a message on every shift change, and have
connected clients subscribe via a WebSocket that forwards Redis messages.
This gives near-instant updates instead of polling. Want me to scaffold
`backend/notifications/redis_pubsub.py` and the WebSocket endpoint?

**User:** ...we already tried that. It's why we're polling right now.

**Assistant:** Ah, I don't have visibility into that history — could you
remind me why it didn't work out, so I don't suggest it again?

**User:** Redis pub/sub silently dropped messages on client reconnect
during deploys, and we're on a free-tier instance with no persistence or
clustering. We reverted it and went back to polling on purpose.

**Assistant:** Got it, thanks for the context. Given that constraint, a
safer real-time option would be Server-Sent Events with a durable
last-event-id... [continues without the wasted round-trip it just cost]

---

**Why this matters:** the "we already tried that" round-trip is unpaid
tax on every session. `cognee-agent-memory` exists to catch exactly this:
recall the `e8c4a71` revert memory unit before the agent ever proposes
Redis pub/sub, and label it HIGH CONFIDENCE (direct, on-topic, not stale)
so the suggestion is never made in the first place.
