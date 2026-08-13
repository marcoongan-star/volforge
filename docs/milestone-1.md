# Milestone 1 — deterministic exchange core

This milestone implements the smallest quantitative slice that can be defended in an interview:

```text
stored scenario + seed
        ↓
synthetic earnings price path
        ↓
Black–Scholes price and Greeks
        ↓
user/agent limit orders
        ↓
risk preset validation
        ↓
price-time-priority fills
```

Prices and quantities in the order book use `Decimal` and integers because binary floating point is unsuitable for exact cash and quantity accounting. Pricing-model outputs remain floating point because numerical approximation is expected there.

The next milestone will combine these components into one ordered session state machine and append commands/events for replay.

