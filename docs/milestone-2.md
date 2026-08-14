# Milestone 2 — append-only session replay

VolForge now places an event log around the matching engine. The order book still decides what trades; the session boundary records every accepted order, cancellation, and resulting fill.

## Why this matters

A trading simulator must be debuggable. Given the same ordered commands, VolForge can rebuild the same book and fills without guessing which mutation happened first. Later milestones will persist these events in PostgreSQL and stream them over WebSockets.

## Data flow

```text
order command
     ↓
matching engine validates and mutates the book
     ↓
session records accepted order
     ↓
session records zero or more fills
     ↓
immutable event view is returned to API/UI consumers
```

Replay reads only command events, runs them through the real matching engine, regenerates fill events, and rejects the replay if the regenerated log differs from the source.
