from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt
from random import Random


@dataclass(frozen=True)
class EarningsScenario:
    """Deterministic synthetic stock path with one earnings jump."""

    initial_price: float = 100.0
    annual_drift: float = 0.0
    annual_volatility: float = 0.24
    earnings_jump_volatility: float = 0.08
    steps_per_year: int = 252

    def path(self, *, seed: int, steps: int, earnings_step: int) -> tuple[float, ...]:
        if steps < 1:
            raise ValueError("steps must be positive")
        if not 1 <= earnings_step <= steps:
            raise ValueError("earnings_step must be inside the path")
        if self.initial_price <= 0 or self.annual_volatility < 0:
            raise ValueError("scenario parameters are invalid")

        random = Random(seed)
        dt = 1.0 / self.steps_per_year
        price = self.initial_price
        prices = [price]
        for step in range(1, steps + 1):
            shock = random.gauss(0.0, 1.0)
            log_return = (
                (self.annual_drift - 0.5 * self.annual_volatility**2) * dt
                + self.annual_volatility * sqrt(dt) * shock
            )
            if step == earnings_step:
                log_return += random.gauss(0.0, self.earnings_jump_volatility)
            price *= exp(log_return)
            prices.append(round(price, 8))
        return tuple(prices)

