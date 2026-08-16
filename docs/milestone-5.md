# Milestone 5: Expected Value and Risk-Adjusted Decisions

VolForge now evaluates a choice through two lenses instead of hiding risk inside one number.

## Expected-value lens

Expected value weights each possible P&L by its probability. It answers: if the same decision could be repeated under the stated beliefs, what is the average payoff?

## Risk-adjusted lens

VolForge also calculates the standard deviation of possible P&L and applies a transparent penalty:

```text
risk-adjusted score = expected P&L - risk aversion × P&L standard deviation
```

Cautious, balanced, and aggressive presets use decreasing risk-aversion values. These are learning-lab preferences, not claims about a universally optimal utility function.

The two benchmarks may disagree. A call can have positive expected value while a cautious user prefers staying flat because the distribution is too wide. Showing both prevents the application from presenting risk preference as mathematical truth.

## Data flow

```text
outcomes + probabilities + option action
                    |
                    v
       P&L distribution and expected value
                    |
                    v
          standard deviation of P&L
                    |
                    v
 expected-value benchmark + risk-adjusted benchmark
                    |
                    v
      opportunity cost under both objectives
```

## Marco's interview explanation

“Expected value and risk preference answer different questions. I preserve expected value, then calculate a separate mean-minus-volatility score using an explicit risk-aversion parameter. A user can therefore see when the mathematically highest-average action conflicts with their tolerance for uncertain outcomes.”
