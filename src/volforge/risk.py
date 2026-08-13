from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class RiskPreset(StrEnum):
    CAUTIOUS = "cautious"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass(frozen=True)
class RiskLimits:
    max_option_inventory: int
    max_absolute_delta: float
    max_order_quantity: int
    max_session_loss: Decimal

    def validate_order(
        self,
        *,
        order_quantity: int,
        projected_inventory: int,
        projected_delta: float,
        current_pnl: Decimal,
    ) -> None:
        if order_quantity <= 0 or order_quantity > self.max_order_quantity:
            raise ValueError("order quantity exceeds the selected risk preset")
        if abs(projected_inventory) > self.max_option_inventory:
            raise ValueError("projected inventory exceeds the selected risk preset")
        if abs(projected_delta) > self.max_absolute_delta:
            raise ValueError("projected delta exceeds the selected risk preset")
        if current_pnl <= -self.max_session_loss:
            raise ValueError("session stop-loss has been reached")


_LIMITS = {
    RiskPreset.CAUTIOUS: RiskLimits(10, 300.0, 2, Decimal("250")),
    RiskPreset.BALANCED: RiskLimits(25, 750.0, 5, Decimal("750")),
    RiskPreset.AGGRESSIVE: RiskLimits(50, 1500.0, 10, Decimal("1500")),
}


def limits_for(preset: RiskPreset) -> RiskLimits:
    return _LIMITS[preset]

