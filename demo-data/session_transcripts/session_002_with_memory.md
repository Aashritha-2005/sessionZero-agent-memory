# Session 002 — with `cognee-agent-memory` attached (target behavior)

**Repo:** ShiftLog (synthetic demo project)
**Date:** 2026-07-01
**Context:** `claude_code_bridge` has queried `recall_service` for
`frontend/components/ShiftCalendar.tsx` and `backend/notifications/*`
before this task starts. This transcript is aspirational — it documents
the intended behavior the bridge should produce once built (Day 2), used
to validate the integration once it's wired up.

---

**[injected context, HIGH CONFIDENCE]**
> Real-time shift-change notifications via Redis pub/sub were tried and
> reverted (commit `e8c4a71`, 2026-05-18): messages were silently dropped
> on client reconnect during deploys on the free-tier Redis instance.
> Replaced with a 10s client poll. Do not re-propose Redis pub/sub without
> addressing the reconnect/durability gap.
> — path length 1, similarity 0.91, age 45 days, no contradictions

**User:** The shift calendar feels laggy when another manager updates a
shift — can you make updates show up in real time instead of the 10s poll?

**Assistant:** Before suggesting anything — this was already attempted via
Redis pub/sub and reverted, because messages were dropped on reconnect
during deploys on the free-tier instance. So I won't re-propose that.
A safer option given that constraint: Server-Sent Events with a durable
`last-event-id` so a reconnecting client can catch up on missed events
without needing Redis's own persistence. Want me to scaffold that?

**[injected context, LOW CONFIDENCE — verify before trusting]**
> Postgres is running locally via Docker (commit `a1f3c02`, 2026-05-04).
> — path length 3, similarity 0.58, age 59 days, **contradicted by**
> commit `2c9e4f1` (2026-06-10): moved to Railway-managed Postgres.
> Flagged low confidence and surfaced instead of silently injected.

**User:** Also, remind me — are we still on local Docker Postgres?

**Assistant:** I have a memory saying yes, but it's flagged LOW CONFIDENCE
because a newer memory contradicts it — looks like the project moved to
Railway-managed Postgres on 2026-06-10. I'd trust the newer one, but
worth a quick confirm since I'm not 100% sure it wasn't reverted again.

---

**Why this matters:** this is demo beat #4, the key differentiator — a
stale memory (local Docker Postgres) is *not* silently injected with the
same confidence as the correct, current one. It's surfaced with its
contradiction and let the user/agent decide.
