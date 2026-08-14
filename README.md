# VolForge

An options market-making laboratory built around a deterministic synthetic-stock earnings event.

VolForge is designed for quantitative-trading interviews: it combines option pricing and Greeks, a price-time-priority matching engine, switchable trader roles, bounded risk presets, delta hedging and explainable P&L attribution. The MVP is educational simulation software—never a brokerage, real-money venue, live-data product or claim of profitable performance.

## Current working features

- Deterministic earnings price paths from a stored seed.
- European Black–Scholes price, delta, gamma, vega and theta.
- Limit-order matching with price-time priority and immutable fills.
- Cautious, balanced and aggressive risk presets.
- Tests for put-call parity, matching priority, bounded risk and replayability.
- Append-only session events for accepted orders, cancellations, and fills.
- Deterministic replay that rebuilds the order book and verifies the regenerated event stream.

The current test suite has eight checks. All example markets are synthetic and explicitly seeded.

## Planned stack

- Python 3.12 for the exchange, pricing, risk and agents.
- FastAPI and WebSockets for commands and live events.
- React and TypeScript for the learning-lab interface.
- PostgreSQL for sessions and the append-only event log.
- pytest, Docker and GitHub Actions for repeatable validation.

## Run the first checks

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
```

## Repository map

| Area | Purpose |
| --- | --- |
| `src/volforge/pricing.py` | Black–Scholes values and Greeks |
| `src/volforge/orderbook.py` | Price-time-priority matching |
| `src/volforge/session.py` | Command boundary, event log, and replay |
| `src/volforge/scenario.py` | Seeded earnings price paths |
| `src/volforge/risk.py` | Cautious, balanced, and aggressive limits |
| `tests/` | Executable examples of every current invariant |
| `docs/` | Short milestone records and data flows |

Start with `tests/test_session_replay.py` to see the Day 2 feature in the smallest readable form. See [Milestone 2](docs/milestone-2.md) for its data flow.

## Next milestones

1. Persist sessions and expose commands through FastAPI.
2. Track cash, option inventory, stock inventory, and marked P&L.
3. Add switchable market-maker and directional agents.
4. Stream the learning lab through WebSockets and a React interface.
