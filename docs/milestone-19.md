# Milestone 19: uncertainty around expected shortfall

Expected shortfall answers, “on average, how bad are the worst 5% of simulated paths?” A single estimate can look precise even when it is based on only 25 tail observations out of 500 paths. VolForge now reports a deterministic nonparametric bootstrap interval around each agent's 5% expected shortfall.

## Algorithm

1. Run the original seeded experiment and retain the full P&L sample.
2. Draw 400 same-size samples with replacement from that empirical distribution.
3. Recalculate 5% expected shortfall for every resample.
4. Sort those estimates and return the 2.5th and 97.5th percentiles.

Separate seeds are derived for the market maker and directional agent, so the result replays exactly without pretending the bootstrap draws are new market observations.

## Interpretation boundary

The interval estimates Monte Carlo sampling uncertainty under the chosen synthetic model. It does not cover model risk, parameter error, execution slippage, or future live performance. A narrow interval can still be confidently wrong if the scenario model is wrong.

## Interview explanation

“VaR gives a loss threshold, while expected shortfall averages losses beyond that threshold. I bootstrapped expected shortfall because tail estimates use relatively few observations and their uncertainty is easy to hide. The bootstrap is deterministic for reproducibility, but I explicitly separate sampling uncertainty from model risk.”
