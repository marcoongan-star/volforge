# Milestone 16: precision-driven sample planning

An inconclusive confidence interval does not automatically mean two strategies are equivalent. It may mean the experiment is too noisy for the effect size the researcher cares about. This milestone converts observed paired dispersion into a transparent path-count requirement.

## Calculation

For paired-difference sample standard deviation `s`, trial count `n`, and normal 95% multiplier `z = 1.96`, the current confidence-interval half-width is:

`margin = z × s / sqrt(n)`

For a target half-width `h`, the estimated required trial count is:

`required trials = ceil((z × s / h)²)`

The planner reports current margin, required trials, additional trials, and whether the current experiment meets the target.

## Measured synthetic example

The existing deterministic 500-path configuration has a paired-difference standard deviation of `$3,262.32`. Its 95% margin is `$285.95`. A target margin of `$250` requires 655 paths, so the current run needs 155 additional paths under the observed-dispersion assumption.

These are reproducible synthetic measurements, not estimates of live profitability.

## Assumptions and failure modes

- The formula treats the observed standard deviation as a planning estimate; a new sample can have different dispersion.
- It uses a normal 95% approximation rather than a small-sample Student-t critical value.
- Precision is not statistical power. Power also requires a chosen alternative effect and Type II error target.
- A narrower interval does not repair biased scenarios, bad calibration, or an economically irrelevant objective.

## Interview explanation

The planner separates statistical uncertainty from economic significance. First define the smallest difference worth resolving, then use measured noise to estimate the computation needed. This is stronger than increasing simulations arbitrarily or declaring an interval that crosses zero to be proof of equality.
