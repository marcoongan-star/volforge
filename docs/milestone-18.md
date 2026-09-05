# Milestone 18 — exact paired sign test

VolForge now reports an exact two-sided sign test beside its mean-P&L confidence interval. For every non-tied synthetic path, it records whether the directional agent or market maker had the larger P&L. Under the null hypothesis, either agent is equally likely to win a paired path.

The exact p-value is:

```text
2 × sum(C(n, i), i = 0..min(wins, losses)) / 2^n
```

Ties are excluded from `n`, and the result is capped at one.

## Why both statistics matter

The mean confidence interval asks whether the average dollar difference is distinguishable from zero. The sign test asks whether one agent wins more often on a typical non-tied path. These can disagree when a strategy loses frequently but occasionally earns a very large payoff.

In the displayed 500-path synthetic scenario, the directional agent wins 163 paths and the maker wins 337. The exact sign test rejects equal win frequency, while the mean-P&L interval still crosses zero. This is not a contradiction; it reveals a skewed payoff distribution.

## Data flow

```text
same seeded terminal path for both agents
                  ↓
paired P&L difference per path
                  ↓
positive / negative / tie counts
                  ↓
exact binomial tail probability
                  ↓
API result + learning-lab explanation
```

## Interview explanation

“I did not let one summary statistic stand in for the whole distribution. The confidence interval estimates an average-dollar effect, while the exact sign test evaluates path-by-path win frequency without assuming normal differences. Their disagreement is economically informative because the directional payoff is highly skewed.”
