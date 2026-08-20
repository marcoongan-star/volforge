from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from .risk import RiskPreset, limits_for


@dataclass(frozen=True)
class QuotePlan:
    theoretical_price: Decimal
    reservation_price: Decimal
    inventory_skew: Decimal
    effective_half_spread: Decimal
    bid_price: Decimal | None
    ask_price: Decimal
    bid_quantity: int
    ask_quantity: int


def _floor_tick(value: Decimal, tick_size: Decimal) -> Decimal:
    return (value / tick_size).to_integral_value(rounding=ROUND_FLOOR) * tick_size


def _ceil_tick(value: Decimal, tick_size: Decimal) -> Decimal:
    return (value / tick_size).to_integral_value(rounding=ROUND_CEILING) * tick_size


def plan_market_maker_quote(
    *,
    theoretical_price: Decimal,
    option_inventory: int,
    max_inventory: int,
    max_order_quantity: int,
    tick_size: Decimal = Decimal("0.01"),
    base_half_spread: Decimal = Decimal("0.05"),
    max_inventory_skew: Decimal = Decimal("0.25"),
    per_contract_fee: Decimal = Decimal("0"),
    contract_multiplier: int = 100,
) -> QuotePlan:
    if theoretical_price <= 0 or tick_size <= 0 or base_half_spread < 0:
        raise ValueError("price and tick size must be positive; spread cannot be negative")
    if max_inventory <= 0 or max_order_quantity <= 0 or contract_multiplier <= 0:
        raise ValueError("inventory, order, and contract limits must be positive")
    if abs(option_inventory) > max_inventory:
        raise ValueError("current inventory exceeds the selected limit")
    if max_inventory_skew < 0 or per_contract_fee < 0:
        raise ValueError("skew and fees cannot be negative")

    inventory_ratio = Decimal(option_inventory) / Decimal(max_inventory)
    inventory_skew = -(inventory_ratio * max_inventory_skew)
    reservation_price = theoretical_price + inventory_skew
    fee_per_option_unit = per_contract_fee / Decimal(contract_multiplier)
    effective_half_spread = base_half_spread + fee_per_option_unit
    raw_bid = reservation_price - effective_half_spread
    raw_ask = reservation_price + effective_half_spread
    bid_price = _floor_tick(raw_bid, tick_size) if raw_bid > 0 else None
    ask_price = max(tick_size, _ceil_tick(raw_ask, tick_size))

    bid_capacity = max_inventory - option_inventory
    ask_capacity = max_inventory + option_inventory
    return QuotePlan(
        theoretical_price=theoretical_price,
        reservation_price=reservation_price,
        inventory_skew=inventory_skew,
        effective_half_spread=effective_half_spread,
        bid_price=bid_price,
        ask_price=ask_price,
        bid_quantity=min(max_order_quantity, bid_capacity) if bid_price else 0,
        ask_quantity=min(max_order_quantity, ask_capacity),
    )


def quote_for_preset(
    preset: RiskPreset,
    **inputs: object,
) -> QuotePlan:
    limits = limits_for(preset)
    return plan_market_maker_quote(
        max_inventory=limits.max_option_inventory,
        max_order_quantity=limits.max_order_quantity,
        **inputs,  # type: ignore[arg-type]
    )
