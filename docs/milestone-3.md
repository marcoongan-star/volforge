# Milestone 3 — cash, inventory, and marked P&L

Every fill now updates a trading ledger for both counterparties.

```text
fill price × contracts × contract multiplier
                    ↓
buyer cash decreases; buyer inventory increases
seller cash increases; seller inventory decreases
                    ↓
current option mark values each inventory
                    ↓
equity = cash + marked inventory value
P&L = equity − starting cash
```

The tests prove two conservation rules: cash transferred by the buyer equals cash received by the seller, and long option inventory equals short option inventory across the pair. When both sides use the same mark, their combined P&L is zero before fees.

Participant starting cash is also recorded as a session event, so replay reconstructs both the exchange and its accounting state.

This milestone intentionally reports total marked P&L. Realized/unrealized attribution, stock hedges, fees, and Greek-based explanations remain later layers.
