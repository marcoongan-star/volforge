# Milestone 8 — Inventory-aware market-making policy

The first market-making policy converts a theoretical option value into a two-sided quote while making its assumptions visible.

1. Start from theoretical value.
2. Shift the reservation price down when inventory is long and up when inventory is short.
3. Add expected fees to the requested half-spread.
4. Round the bid down and ask up to valid ticks.
5. Reduce or disable the side that would breach the selected inventory limit.

This is not a claim that the quotes are profitable. It is a deterministic policy for studying the tradeoff between spread capture, inventory risk, transaction costs, and fill probability. Cautious, balanced, and aggressive presets change the maximum inventory and order size without allowing unlimited risk.
