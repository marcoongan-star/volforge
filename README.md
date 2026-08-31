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
- A responsive React/TypeScript learning lab with pause, step, autoplay, quote-risk controls, delta math, and P&L attribution.
- Cursor-based event recovery that resumes after the last confirmed sequence without rebuilding or inventing exchange state.
- WebSocket sequence notifications that direct reconnecting clients back to the durable HTTP recovery path.
- Common-random-number volatility sensitivity analysis that tests whether a paired agent conclusion is robust to model assumptions.
- An empirical variance-reduction diagnostic with covariance, correlation, paired versus unpaired standard error, and simulation-efficiency reconciliation.

All example markets are synthetic and explicitly seeded.

## Stack

- Python 3.12 for the exchange, pricing, risk and agents.
- FastAPI for commands and analysis, with WebSockets for low-latency sequence notifications.
- React 19, TypeScript, and vinext for the learning-lab interface and free public build.
- PostgreSQL for sessions and the append-only event log.
- pytest, Docker and GitHub Actions for repeatable validation.

## Run the first checks

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
```

Start the public learning lab in a second terminal:

```bash
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:3000`. The hosted demonstration uses a clearly labeled synthetic replay; the durable Python session API remains the source of truth for accepted orders, fills, hedges, inventory, and cash when connected.

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
| `src/volforge/api.py` | Stateless analysis, stateful exchange HTTP, and WebSocket notification boundaries |
| `frontend/app/trading-lab.tsx` | Interactive replay controls, delta explanation, and P&L view |
| `frontend/app/globals.css` | Product styling and responsive layout |
| `tests/` | Executable examples of every current invariant |
| `docs/` | Short milestone records and data flows |

Start with `tests/test_decisions.py` for the smallest quantitative example. See [Milestone 2](docs/milestone-2.md) for replay, [Milestone 3](docs/milestone-3.md) for the ledger data flow, [Milestone 4](docs/milestone-4.md) for expected value and statistical experiments, [Milestone 5](docs/milestone-5.md) for dual decision benchmarks, [Milestone 6](docs/milestone-6.md) for the hybrid API, [Milestone 7](docs/milestone-7.md) for delta hedging and P&L attribution, [Milestone 8](docs/milestone-8.md) for inventory-aware quoting, [Milestone 9](docs/milestone-9.md) for reconnect-by-sequence recovery, [Milestone 10](docs/milestone-10.md) for WebSocket notifications over that recovery layer, [Milestone 11](docs/milestone-11.md) for comparing market-making and directional objectives, [Milestone 12](docs/milestone-12.md) for paired-path distributions and expected shortfall, [Milestone 13](docs/milestone-13.md) for paired confidence intervals and effect size, [Milestone 14](docs/milestone-14.md) for common-random-number volatility sensitivity, [Milestone 15](docs/milestone-15.md) for empirical variance-reduction efficiency, and [Milestone 16](docs/milestone-16.md) for precision-driven sample planning.

## Next milestones

1. Connect the public replay adapter to a deployed FastAPI session.
2. Connect the public lab to the tested WebSocket and recovery endpoints.
