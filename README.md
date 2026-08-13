# VolForge

An options market-making laboratory built around a deterministic synthetic-stock earnings event.

VolForge is designed for quantitative-trading interviews: it combines option pricing and Greeks, a price-time-priority matching engine, switchable trader roles, bounded risk presets, delta hedging and explainable P&L attribution. The MVP is educational simulation software—never a brokerage, real-money venue, live-data product or claim of profitable performance.

## Milestone 1

- Deterministic earnings price paths from a stored seed.
- European Black–Scholes price, delta, gamma, vega and theta.
- Limit-order matching with price-time priority and immutable fills.
- Cautious, balanced and aggressive risk presets.
- Tests for put-call parity, matching priority, bounded risk and replayability.

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

All example markets are synthetic and explicitly seeded.

