# VolForge contributor guide

Marco owns product and trading-simulation decisions. Codex implements, tests and explains them.

## Approved product constraints

- The public scenario is a synthetic stock earnings event.
- Users can switch between market-maker and directional-trader roles.
- The first universe is one synthetic stock and its European options chain.
- Users choose cautious, balanced or aggressive risk presets; aggressive never means unlimited.
- The interface should feel like an approachable learning lab, not a generic terminal clone.
- Sessions are deterministic and replayable from configuration, commands and random seed.
- No real money, brokerage connection, fabricated live feed or profitability claim.

## Working style

- Keep teaching and interview explanations out of the product UI; put them in `docs/` and explain them directly to Marco.
- Treat matching, accounting, risk and replay properties as invariants backed by tests.
- Never use floating-point values for order prices, quantities or cash accounting.
- Every market-data example must be labeled synthetic or cited to a permitted source.
- Prefer small milestones Marco can later modify and explain.

