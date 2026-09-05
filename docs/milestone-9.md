# Milestone 9 — cursor-based event recovery

## Product slice

VolForge now exposes `GET /v1/sessions/{session_id}/events?after_sequence=N`. It returns the canonical suffix after the client's last confirmed event, a next cursor, and a `has_more` signal. The learning lab demonstrates disconnecting and resuming from that cursor.

## Why a cursor comes before WebSockets

A WebSocket improves delivery latency but does not solve recovery by itself. Connections drop, devices sleep, and messages can be missed. The durable append-only log and monotonic sequence are the correctness layer; a future WebSocket is only the fast notification path.

```text
command -> append event N -> durable SQLite/PostgreSQL log
                              |
                              v
                     WebSocket notification (future)
                              |
client disconnects             x
client reconnects -> GET events after last confirmed N
                              |
                              v
                 apply contiguous N+1 ... latest
```

## Invariants

- Event sequence is positive, contiguous, and session-scoped.
- Recovery never reads before or at the supplied cursor.
- Pagination never advances the cursor past an event that was not delivered.
- An unknown session returns 404; an invalid negative cursor returns 422.
- The browser never fabricates fills, inventory, cash, or P&L while offline.

## Interview explanation

The event log is both the audit trail and the replay source. Cursor recovery makes correctness independent of WebSocket uptime. This is the same pattern used by resumable feeds: durable ordered facts first, low-latency transport second.
