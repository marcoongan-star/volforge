# Milestone 17 — power-aware experiment design

VolForge now answers two separate questions before spending more simulation paths:

1. **Precision:** how many paired paths are needed to make the confidence interval no wider than a chosen half-width?
2. **Power:** how many paired paths are needed to detect a chosen economically meaningful difference with a specified probability?

The new power planner uses the observed standard deviation of the paired P&L differences. For a two-sided normal approximation it computes:

`n = ceil(((z_(1-alpha/2) + z_power) * paired_sd / target_difference) ** 2)`

It also reports approximate achieved power at the current path count. The defaults are a 5% significance level, 80% target power, and a $500 detectable difference.

## Data flow

```text
same seeded paths
      ↓
directional P&L − market-maker P&L for every path
      ↓
paired standard deviation
      ↓
power planner + precision planner
      ↓
required paths, additional paths, and achieved power
```

## Important boundary

Power does not say the strategy works. It describes a test design under an assumed effect size. Choosing a tiny target effect can require many paths; choosing an unrealistically large target can make a weak experiment look adequately powered. The target therefore needs an economic justification.

## Interview explanation

“I separated confidence-interval precision from statistical power. Both consume the paired-difference variance, but precision targets an estimation width while power targets the probability of detecting a preselected effect. This prevents me from choosing the number of simulations only after seeing a favorable result.”
