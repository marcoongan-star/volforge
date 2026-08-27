# Milestone 13 — Paired uncertainty and effect size

The previous experiment reported the observed average difference between two agents. This milestone asks the more important analytical question: how noisy is that difference?

For each synthetic path, VolForge calculates:

```text
paired difference = directional P&L - market-maker P&L
```

It then reports the paired-difference standard deviation, standard error of the mean, a large-sample 95% confidence interval, and the standardized paired effect.

## Why pairing changes the calculation

The observations are not two unrelated samples. Both agents trade the same path, so inference should operate on one list of within-path differences. Treating the strategies as independent would discard that experimental design and usually add avoidable noise.

For `n` paired differences with sample mean `d_bar` and sample standard deviation `s_d`:

```text
standard error = s_d / sqrt(n)
95% interval   = d_bar ± 1.96 * standard error
paired effect  = d_bar / s_d
```

The 1.96 interval is a large-sample normal approximation, appropriate for the displayed 500-path experiment but not a substitute for distributional diagnostics or out-of-sample evidence.

## Reading the displayed result

The directional agent's observed mean exceeds the maker by $22.88, but its 95% interval runs from -$263.08 to +$308.83 and its standardized effect is 0.0070. The interval crosses zero by a wide margin. The honest conclusion is not “directional wins”; it is that this experiment does not establish a clear average advantage.

That distinction is the purpose of the feature. A point estimate is an outcome. Uncertainty describes how much evidence that outcome contains.

## Interview explanation

“I used common random numbers and analyzed the within-path P&L difference. The paired mean was positive, but the standard error was large and the 95% interval crossed zero. I therefore displayed the result as inconclusive instead of turning simulation noise into a strategy claim. I also reported tail loss separately because uncertainty about the mean and downside risk answer different questions.”
