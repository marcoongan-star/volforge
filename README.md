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
- Fill accounting for participant cash and option inventory.
- Mark-to-market equity and P&L using an explicit option mark and contract multiplier.
- Discrete earnings beliefs with expected-value comparison of buying, selling, or staying flat.
- Decision review that measures opportunity cost against the best action under stated beliefs.
- Side-by-side expected-value and risk-adjusted benchmarks using payoff dispersion.
- Reproducible long-straddle experiments with dispersion, standard error, and 95% confidence intervals.
- SQLite-backed append-only session storage with deterministic restart recovery.
- A hybrid FastAPI boundary: stateless earnings analysis plus durable exchange commands.
- Delta-targeted stock hedging with explicit per-share and fixed transaction fees.
- Reconciled P&L attribution across option inventory, stock hedges, and fees.
- Inventory-skewed, fee-aware two-sided quote plans bounded by the selected risk preset.

All example markets are synthetic and explicitly seeded.

## Planned stack

- Python 3.12 for the exchange, pricing, risk and agents.
- FastAPI for commands and analysis; WebSockets are the next live-event boundary.
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
| `src/volforge/ledger.py` | Cash, inventory, equity, and marked P&L |
| `src/volforge/scenario.py` | Seeded earnings price paths |
| `src/volforge/risk.py` | Cautious, balanced, and aggressive limits |
| `src/volforge/decisions.py` | Probability-weighted earnings decisions and benchmark review |
| `src/volforge/experiments.py` | Repeatable strategy experiments and uncertainty estimates |
| `src/volforge/store.py` | SQLite session metadata and append-only events |
| `src/volforge/api.py` | Stateless analysis and stateful exchange HTTP boundaries |
| `tests/` | Executable examples of every current invariant |
| `docs/` | Short milestone records and data flows |

Start with `tests/test_decisions.py` for the smallest quantitative example. See [Milestone 2](docs/milestone-2.md) for replay, [Milestone 3](docs/milestone-3.md) for the ledger data flow, [Milestone 4](docs/milestone-4.md) for expected value and statistical experiments, [Milestone 5](docs/milestone-5.md) for dual decision benchmarks, [Milestone 6](docs/milestone-6.md) for the hybrid API, [Milestone 7](docs/milestone-7.md) for delta hedging and P&L attribution, and [Milestone 8](docs/milestone-8.md) for inventory-aware quoting.

## Next milestones

1. Add stock inventory, delta hedging, fees, and P&L attribution.
2. Add switchable market-maker and directional agents.
3. Stream the learning lab through WebSockets and a React interface.
