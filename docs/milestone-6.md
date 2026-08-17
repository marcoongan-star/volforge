# Milestone 6 — Hybrid API and durable sessions

VolForge now separates two kinds of work instead of forcing everything into one storage model.

## Stateless analysis path

`POST /v1/analysis/earnings` accepts the user's probability-weighted earnings beliefs, calculates each action's payoff distribution, and returns expected-value and risk-adjusted benchmarks. The request is not saved. The same inputs always produce the same output.

## Stateful exchange path

Session commands use an append-only SQLite event store:

`HTTP command → load metadata/events → deterministic replay → validate command → append only new events → return current state`

The event log is the source of truth. Active orders are rebuilt rather than stored as a second mutable truth, which makes a session explainable and replayable after a restart.

SQLite keeps local setup free and simple. The storage boundary is intentionally separate from the exchange core, so PostgreSQL can replace it for multi-user deployment without rewriting matching, accounting, or replay logic.

## Invariants covered by tests

- Event sequences are contiguous and cannot be rewritten.
- Duplicate session identifiers are rejected.
- A restarted API rebuilds the same active order book.
- Earnings analysis labels itself stateless and does not create a session.
- Monetary inputs remain `Decimal` values and cross JSON boundaries as strings.
