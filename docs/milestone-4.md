# Milestone 4 — expected value and statistical experiments

This milestone turns the exchange foundation into a quantitative decision lab.

## Decision analysis

A user states a discrete earnings belief: possible stock returns and probabilities that sum to one. VolForge calculates the call P&L in every state and compares buying, selling, and staying flat.

```text
subjective outcomes + probabilities + option price
                         |
                         v
              payoff in every outcome
                         |
                         v
     expected P&L + downside + probability of profit
                         |
                         v
         chosen action versus EV benchmark
```

The review grades the decision from information available before the event. It does not call a decision good merely because one random outcome made money.

## Repeated experiment

The long-straddle experiment runs the same strategy across consecutive deterministic seeds. It reports mean P&L, sample standard deviation, standard error, a 95% confidence interval, probability of profit, and extremes.

This answers a more rigorous question than “did the strategy win once?”: under the stated synthetic process, what is the estimated distribution, and how uncertain is the estimate?

## Marco's interview explanation

“I separated subjective decision analysis from Monte Carlo model analysis. The first asks what action has the best expected value under a user's stated beliefs. The second samples many synthetic paths and attaches uncertainty to the estimated average. Both preserve their inputs and seeds, so results can be challenged and replayed.”
