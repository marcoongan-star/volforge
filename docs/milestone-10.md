# Milestone 10 — WebSocket notifications over durable recovery

## Product slice

VolForge now exposes `/v1/sessions/{session_id}/stream`. A client supplies its last confirmed sequence. The socket announces that newer sequences exist and points to the HTTP recovery endpoint; it does not become a second source of exchange truth.

## Architecture

```text
append-only SQLite event log
        |                 \
        |                  WebSocket: "events through N exist"
        |                                 |
HTTP cursor recovery <---------------- client
        |
ordered event payloads
```

The socket is deliberately thin. It polls the durable log, emits sequence metadata, responds to a heartbeat, and closes an unknown session with an application-specific code. Payload recovery still uses the bounded, tested HTTP cursor endpoint.

## Why this split matters

- WebSocket connections are fast but temporary.
- The append-only event log survives disconnects and process restarts.
- A notification may be repeated without duplicating an order or fill.
- A sleeping client can recover later without having kept its socket alive.

## Interview explanation

"I separated notification latency from recovery correctness. WebSockets tell the UI that its cursor is stale; the durable ordered log supplies the missing payloads. That lets the socket fail without losing exchange state."
