# Milestone 11 — Competing trading-agent objectives

## Product slice

The learning lab can now switch between two agents that observe the same option market but solve different problems:

- The market maker posts a bid and ask to earn spread while skewing quotes away from unwanted inventory.
- The directional agent buys, sells, or stays flat based on a forecast, confidence, costs, scenario uncertainty, and the selected risk preset.

## Directional rule

```text
raw edge = forecast price - theoretical price
weighted edge = confidence × raw edge
risk hurdle = transaction cost
             + preset penalty × (1 - confidence) × scenario volatility

trade only when |weighted edge| > risk hurdle
```

Quantity increases with edge after the hurdle but is capped by the preset's maximum order size. Exact equality stays flat because uncertain upside should not be treated as free.

## Why this helps a quant interview

The result distinguishes a forecast from an executable decision. A model can predict a higher value and still recommend no trade when confidence is low, costs are high, or uncertainty is large. It also shows that market making is not merely “guess the direction”; its edge and risk come from spread, flow, and inventory.

## Data flow

`synthetic inputs → stateless agent comparison → risk-gated actions → browser explanation`

This endpoint does not write exchange state. If a chosen action is later submitted to a session, the existing order, fill, ledger, hedge, and event-log paths become authoritative.

## Interview explanation

“I made two strategies comparable without pretending they have the same objective. The directional policy needs forecast edge to clear a cost-and-uncertainty hurdle. The market maker instead quotes both sides and shifts its reservation price based on inventory. The UI lets a user inspect that difference on the same replay.”
