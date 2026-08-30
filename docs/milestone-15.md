# Milestone 15: measuring variance-reduction efficiency

VolForge already compares both agents on identical synthetic paths. This milestone checks whether that pairing actually improves the precision of the estimated mean P&L difference.

## First principles

For independent samples, the variance of a difference in sample means is the sum of the two mean variances. For paired samples, covariance matters:

```text
Var(Directional - Maker)
  = Var(Directional) + Var(Maker) - 2 Cov(Directional, Maker)
```

Positive covariance reduces the paired-difference variance; negative covariance increases it. Common random numbers are therefore a technique to test, not a phrase that automatically guarantees a better experiment.

VolForge now reports sample covariance, path correlation, the hypothetical unpaired standard error, the observed paired standard error, and an efficiency ratio:

```text
efficiency = unpaired standard error / paired standard error
```

Values above one mean pairing improved precision. Values below one mean it made precision worse.

## Measured synthetic result

For the published 500-path experiment, path correlation is only +0.0284. The unpaired standard error is $146.29 and the paired standard error is $145.90, giving a 1.0027× efficiency ratio. Pairing lowers error by about 0.27%—a real but very modest improvement.

This matters because VolForge now evaluates its own simulation method instead of assuming it is effective. A future extension can search for shock decompositions that create stronger positive covariance without changing either agent's marginal path distribution.

## What Marco should understand

Variance reduction improves estimate precision without necessarily adding more trials. Its effectiveness depends on the covariance induced by the experimental design. In an interview, the important move is to derive the paired-variance identity and then verify the empirical correlation rather than asserting that common random numbers always help.

## Verification

- All 44 Python tests pass.
- The efficiency ratio reconciles to the two reported standard errors.
- The API returns the full diagnostic with the synthetic-data warning.
- Frontend lint, production build, and both server-render checks pass.
