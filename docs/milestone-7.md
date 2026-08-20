# Milestone 7 — Delta hedging and explainable P&L

VolForge can now hedge a participant's option delta with the synthetic underlying stock. For an option inventory `q`, per-contract multiplier `m`, and option delta `Δ`, the target stock position is:

`target shares = round(-q × m × Δ)`

The rebalance trades only the difference between the current and target stock positions. Per-share and fixed transaction fees are charged only when a trade occurs.

## P&L attribution

Total marked P&L reconciles exactly into:

`option P&L + hedge P&L - transaction fees = total P&L = equity - starting cash`

This separation matters because a positive total does not reveal whether the option quote, the stock hedge, or luck in the underlying move produced it.

Every stock hedge is appended to the session event log with its execution price, signed quantity, fee, input delta, and resulting stock inventory. Restarting the API replays the option fills and stock hedge into the same account state.
