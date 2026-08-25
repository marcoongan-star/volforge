from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from enum import StrEnum

from .risk import RiskPreset, limits_for


class DirectionalAction(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True)
class DirectionalPlan:
    action: DirectionalAction
    quantity: int
    raw_edge: Decimal
    confidence_weighted_edge: Decimal
    risk_hurdle: Decimal
    edge_after_hurdle: Decimal


_UNCERTAINTY_PENALTY = {
    RiskPreset.CAUTIOUS: Decimal("1.00"),
    RiskPreset.BALANCED: Decimal("0.60"),
    RiskPreset.AGGRESSIVE: Decimal("0.25"),
}


def plan_directional_trade(
    *,
    theoretical_price: Decimal,
    forecast_price: Decimal,
    confidence: Decimal,
    scenario_volatility: Decimal,
    transaction_cost: Decimal,
    risk_preset: RiskPreset = RiskPreset.BALANCED,
) -> DirectionalPlan:
    """Turn a price forecast into a risk-gated, one-sided option decision."""
    if theoretical_price <= 0 or forecast_price <= 0:
        raise ValueError("theoretical and forecast prices must be positive")
    if not Decimal("0") <= confidence <= Decimal("1"):
        raise ValueError("confidence must be between zero and one")
    if scenario_volatility <= 0 or transaction_cost < 0:
        raise ValueError("scenario volatility must be positive and costs cannot be negative")

    raw_edge = forecast_price - theoretical_price
    weighted_edge = confidence * raw_edge
    uncertainty = (Decimal("1") - confidence) * scenario_volatility
    risk_hurdle = transaction_cost + _UNCERTAINTY_PENALTY[risk_preset] * uncertainty
    edge_after_hurdle = abs(weighted_edge) - risk_hurdle
    if edge_after_hurdle <= 0 or raw_edge == 0:
        return DirectionalPlan(
            action=DirectionalAction.HOLD,
            quantity=0,
            raw_edge=raw_edge,
            confidence_weighted_edge=weighted_edge,
            risk_hurdle=risk_hurdle,
            edge_after_hurdle=edge_after_hurdle,
        )

    max_quantity = limits_for(risk_preset).max_order_quantity
    utilization = min(Decimal("1"), edge_after_hurdle / scenario_volatility)
    quantity = max(
        1,
        int((Decimal(max_quantity) * utilization).to_integral_value(rounding=ROUND_FLOOR)),
    )
    return DirectionalPlan(
        action=DirectionalAction.BUY if raw_edge > 0 else DirectionalAction.SELL,
        quantity=quantity,
        raw_edge=raw_edge,
        confidence_weighted_edge=weighted_edge,
        risk_hurdle=risk_hurdle,
        edge_after_hurdle=edge_after_hurdle,
    )
