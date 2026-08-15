from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .scenario import EarningsScenario


CENT = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


@dataclass(frozen=True)
class ExperimentResult:
    trials: int
    mean_pnl: Decimal
    pnl_standard_deviation: Decimal
    standard_error: Decimal
    confidence_interval_95: tuple[Decimal, Decimal]
    probability_of_profit: Decimal
    best_pnl: Decimal
    worst_pnl: Decimal
    base_seed: int


def run_long_straddle_experiment(
    scenario: EarningsScenario,
    *,
    strike: Decimal,
    total_premium: Decimal,
    trials: int,
    base_seed: int,
    steps: int = 20,
    earnings_step: int = 10,
    contract_multiplier: int = 100,
) -> ExperimentResult:
    """Estimate a long straddle's earnings P&L distribution on reproducible paths."""
    if strike <= 0:
        raise ValueError("strike must be positive")
    if total_premium < 0:
        raise ValueError("total premium cannot be negative")
    if trials < 2:
        raise ValueError("at least two trials are required for uncertainty estimates")
    if contract_multiplier <= 0:
        raise ValueError("contract multiplier must be positive")

    scale = Decimal(contract_multiplier)
    pnls: list[Decimal] = []
    for offset in range(trials):
        path = scenario.path(
            seed=base_seed + offset,
            steps=steps,
            earnings_step=earnings_step,
        )
        terminal_spot = Decimal(str(path[-1]))
        payoff = abs(terminal_spot - strike)
        pnls.append(((payoff - total_premium) * scale).quantize(CENT, rounding=ROUND_HALF_UP))

    count = Decimal(trials)
    mean = sum(pnls, start=Decimal("0")) / count
    sample_variance = sum(((pnl - mean) ** 2 for pnl in pnls), start=Decimal("0")) / (
        count - Decimal("1")
    )
    standard_deviation = sample_variance.sqrt()
    standard_error = standard_deviation / count.sqrt()
    margin = Decimal("1.96") * standard_error
    probability_of_profit = Decimal(sum(pnl > 0 for pnl in pnls)) / count

    return ExperimentResult(
        trials=trials,
        mean_pnl=mean.quantize(CENT, rounding=ROUND_HALF_UP),
        pnl_standard_deviation=standard_deviation.quantize(CENT, rounding=ROUND_HALF_UP),
        standard_error=standard_error.quantize(CENT, rounding=ROUND_HALF_UP),
        confidence_interval_95=(
            (mean - margin).quantize(CENT, rounding=ROUND_HALF_UP),
            (mean + margin).quantize(CENT, rounding=ROUND_HALF_UP),
        ),
        probability_of_profit=probability_of_profit.quantize(
            FOUR_PLACES, rounding=ROUND_HALF_UP
        ),
        best_pnl=max(pnls),
        worst_pnl=min(pnls),
        base_seed=base_seed,
    )
