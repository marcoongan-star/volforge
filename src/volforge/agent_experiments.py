from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from .agents import DirectionalAction, plan_directional_trade
from .contracts import OptionType
from .market_maker import quote_for_preset
from .pricing import black_scholes
from .risk import RiskPreset
from .scenario import EarningsScenario


CENT = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


@dataclass(frozen=True)
class AgentDistribution:
    mean_pnl: Decimal
    pnl_standard_deviation: Decimal
    probability_of_profit: Decimal
    percentile_05: Decimal
    expected_shortfall_05: Decimal
    best_pnl: Decimal
    worst_pnl: Decimal


@dataclass(frozen=True)
class AgentComparisonExperiment:
    trials: int
    base_seed: int
    directional_action: DirectionalAction
    directional_quantity: int
    market_maker: AgentDistribution
    directional: AgentDistribution
    mean_directional_minus_maker: Decimal
    paired_difference_standard_deviation: Decimal
    paired_difference_standard_error: Decimal
    unpaired_difference_standard_error: Decimal
    paired_covariance: Decimal
    paired_correlation: Decimal
    common_random_number_efficiency: Decimal
    paired_mean_ci_95_low: Decimal
    paired_mean_ci_95_high: Decimal
    paired_standardized_effect: Decimal
    probability_directional_outperforms: Decimal


@dataclass(frozen=True)
class SensitivityCell:
    earnings_jump_volatility: Decimal
    mean_directional_minus_maker: Decimal
    paired_mean_ci_95_low: Decimal
    paired_mean_ci_95_high: Decimal
    market_maker_expected_shortfall_05: Decimal
    directional_expected_shortfall_05: Decimal
    conclusion: str


@dataclass(frozen=True)
class AgentSensitivityExperiment:
    trials_per_level: int
    base_seed: int
    cells: tuple[SensitivityCell, ...]
    stable_conclusion: bool


def _distribution(pnls: list[Decimal]) -> AgentDistribution:
    count = Decimal(len(pnls))
    mean = sum(pnls, start=Decimal("0")) / count
    sample_variance = sum(
        ((pnl - mean) ** 2 for pnl in pnls), start=Decimal("0")
    ) / (count - Decimal("1"))
    sorted_pnls = sorted(pnls)
    percentile_index = int((len(sorted_pnls) - 1) * 0.05)
    tail_count = max(1, ceil(len(sorted_pnls) * 0.05))
    expected_shortfall = sum(sorted_pnls[:tail_count], start=Decimal("0")) / Decimal(
        tail_count
    )
    return AgentDistribution(
        mean_pnl=mean.quantize(CENT, rounding=ROUND_HALF_UP),
        pnl_standard_deviation=sample_variance.sqrt().quantize(
            CENT, rounding=ROUND_HALF_UP
        ),
        probability_of_profit=(
            Decimal(sum(pnl > 0 for pnl in pnls)) / count
        ).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP),
        percentile_05=sorted_pnls[percentile_index],
        expected_shortfall_05=expected_shortfall.quantize(CENT, rounding=ROUND_HALF_UP),
        best_pnl=max(pnls),
        worst_pnl=min(pnls),
    )


def run_agent_comparison_experiment(
    scenario: EarningsScenario,
    *,
    strike: Decimal,
    forecast_option_price: Decimal,
    confidence: Decimal,
    scenario_option_volatility: Decimal,
    transaction_cost: Decimal,
    risk_preset: RiskPreset,
    trials: int,
    base_seed: int,
    years_to_expiry: float = 30 / 365,
    risk_free_rate: float = 0.04,
    option_volatility: float = 0.35,
    steps: int = 20,
    earnings_step: int = 10,
    contract_multiplier: int = 100,
) -> AgentComparisonExperiment:
    """Compare different objectives on identical reproducible synthetic paths."""
    if strike <= 0 or trials < 2 or contract_multiplier <= 0:
        raise ValueError("strike and multiplier must be positive; at least two trials are required")
    initial_spot = Decimal(str(scenario.initial_price))
    initial_metrics = black_scholes(
        OptionType.CALL,
        scenario.initial_price,
        float(strike),
        years_to_expiry,
        risk_free_rate,
        option_volatility,
    )
    theoretical_price = Decimal(str(initial_metrics.price))
    initial_delta = Decimal(str(initial_metrics.delta))
    directional_plan = plan_directional_trade(
        theoretical_price=theoretical_price,
        forecast_price=forecast_option_price,
        confidence=confidence,
        scenario_volatility=scenario_option_volatility,
        transaction_cost=transaction_cost,
        risk_preset=risk_preset,
    )
    maker_quote = quote_for_preset(
        risk_preset,
        theoretical_price=theoretical_price,
        option_inventory=0,
        per_contract_fee=transaction_cost * Decimal(contract_multiplier),
        contract_multiplier=contract_multiplier,
    )
    if maker_quote.bid_price is None:
        raise ValueError("market-maker bid is unavailable for these inputs")

    scale = Decimal(contract_multiplier)
    maker_pnls: list[Decimal] = []
    directional_pnls: list[Decimal] = []
    for offset in range(trials):
        path = scenario.path(
            seed=base_seed + offset,
            steps=steps,
            earnings_step=earnings_step,
        )
        terminal_spot = Decimal(str(path[-1]))
        terminal_call = max(Decimal("0"), terminal_spot - strike)

        customer_buys = (base_seed + offset) % 2 == 0
        option_position = Decimal("-1") if customer_buys else Decimal("1")
        fill_price = maker_quote.ask_price if customer_buys else maker_quote.bid_price
        stock_hedge = -(option_position * initial_delta * scale).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        maker_option_pnl = option_position * (terminal_call - fill_price) * scale
        maker_hedge_pnl = stock_hedge * (terminal_spot - initial_spot)
        maker_cost = transaction_cost * scale
        maker_pnls.append(
            (maker_option_pnl + maker_hedge_pnl - maker_cost).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
        )

        quantity_scale = Decimal(directional_plan.quantity) * scale
        if directional_plan.action is DirectionalAction.BUY:
            directional_pnl = (
                terminal_call - theoretical_price - transaction_cost
            ) * quantity_scale
        elif directional_plan.action is DirectionalAction.SELL:
            directional_pnl = (
                theoretical_price - terminal_call - transaction_cost
            ) * quantity_scale
        else:
            directional_pnl = Decimal("0")
        directional_pnls.append(directional_pnl.quantize(CENT, rounding=ROUND_HALF_UP))

    maker_distribution = _distribution(maker_pnls)
    directional_distribution = _distribution(directional_pnls)
    paired_differences = [
        directional - maker
        for directional, maker in zip(directional_pnls, maker_pnls, strict=True)
    ]
    paired_mean = sum(paired_differences, start=Decimal("0")) / Decimal(trials)
    paired_variance = sum(
        ((difference - paired_mean) ** 2 for difference in paired_differences),
        start=Decimal("0"),
    ) / Decimal(trials - 1)
    paired_standard_deviation = paired_variance.sqrt()
    paired_standard_error = paired_standard_deviation / Decimal(trials).sqrt()
    maker_mean = sum(maker_pnls, start=Decimal("0")) / Decimal(trials)
    directional_mean = sum(directional_pnls, start=Decimal("0")) / Decimal(trials)
    maker_variance = sum(
        ((pnl - maker_mean) ** 2 for pnl in maker_pnls), start=Decimal("0")
    ) / Decimal(trials - 1)
    directional_variance = sum(
        ((pnl - directional_mean) ** 2 for pnl in directional_pnls),
        start=Decimal("0"),
    ) / Decimal(trials - 1)
    paired_covariance = sum(
        (
            (directional - directional_mean) * (maker - maker_mean)
            for directional, maker in zip(directional_pnls, maker_pnls, strict=True)
        ),
        start=Decimal("0"),
    ) / Decimal(trials - 1)
    unpaired_standard_error = (
        (directional_variance + maker_variance) / Decimal(trials)
    ).sqrt()
    correlation_denominator = (directional_variance * maker_variance).sqrt()
    paired_correlation = (
        paired_covariance / correlation_denominator
        if correlation_denominator != 0
        else Decimal("0")
    )
    common_random_number_efficiency = (
        unpaired_standard_error / paired_standard_error
        if paired_standard_error != 0
        else Decimal("0")
    )
    normal_95_margin = Decimal("1.96") * paired_standard_error
    standardized_effect = (
        paired_mean / paired_standard_deviation
        if paired_standard_deviation != 0
        else Decimal("0")
    )
    return AgentComparisonExperiment(
        trials=trials,
        base_seed=base_seed,
        directional_action=directional_plan.action,
        directional_quantity=directional_plan.quantity,
        market_maker=maker_distribution,
        directional=directional_distribution,
        mean_directional_minus_maker=paired_mean.quantize(CENT, rounding=ROUND_HALF_UP),
        paired_difference_standard_deviation=paired_standard_deviation.quantize(
            CENT, rounding=ROUND_HALF_UP
        ),
        paired_difference_standard_error=paired_standard_error.quantize(
            CENT, rounding=ROUND_HALF_UP
        ),
        unpaired_difference_standard_error=unpaired_standard_error.quantize(
            CENT, rounding=ROUND_HALF_UP
        ),
        paired_covariance=paired_covariance.quantize(CENT, rounding=ROUND_HALF_UP),
        paired_correlation=paired_correlation.quantize(
            FOUR_PLACES, rounding=ROUND_HALF_UP
        ),
        common_random_number_efficiency=common_random_number_efficiency.quantize(
            FOUR_PLACES, rounding=ROUND_HALF_UP
        ),
        paired_mean_ci_95_low=(paired_mean - normal_95_margin).quantize(
            CENT, rounding=ROUND_HALF_UP
        ),
        paired_mean_ci_95_high=(paired_mean + normal_95_margin).quantize(
            CENT, rounding=ROUND_HALF_UP
        ),
        paired_standardized_effect=standardized_effect.quantize(
            FOUR_PLACES, rounding=ROUND_HALF_UP
        ),
        probability_directional_outperforms=(
            Decimal(sum(difference > 0 for difference in paired_differences))
            / Decimal(trials)
        ).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP),
    )


def run_agent_sensitivity_experiment(
    *,
    initial_price: Decimal,
    annual_volatility: Decimal,
    earnings_jump_volatilities: tuple[Decimal, ...],
    strike: Decimal,
    forecast_option_price: Decimal,
    confidence: Decimal,
    scenario_option_volatility: Decimal,
    transaction_cost: Decimal,
    risk_preset: RiskPreset,
    trials: int,
    base_seed: int,
) -> AgentSensitivityExperiment:
    """Stress one conclusion across earnings-jump assumptions using common seeds."""
    if initial_price <= 0 or annual_volatility < 0:
        raise ValueError("initial price must be positive and annual volatility cannot be negative")
    if not earnings_jump_volatilities:
        raise ValueError("at least one earnings jump volatility is required")
    if len(set(earnings_jump_volatilities)) != len(earnings_jump_volatilities):
        raise ValueError("earnings jump volatility levels must be unique")
    if any(level < 0 for level in earnings_jump_volatilities):
        raise ValueError("earnings jump volatility cannot be negative")

    cells: list[SensitivityCell] = []
    for level in sorted(earnings_jump_volatilities):
        result = run_agent_comparison_experiment(
            EarningsScenario(
                initial_price=float(initial_price),
                annual_volatility=float(annual_volatility),
                earnings_jump_volatility=float(level),
            ),
            strike=strike,
            forecast_option_price=forecast_option_price,
            confidence=confidence,
            scenario_option_volatility=scenario_option_volatility,
            transaction_cost=transaction_cost,
            risk_preset=risk_preset,
            trials=trials,
            base_seed=base_seed,
        )
        if result.paired_mean_ci_95_low > 0:
            conclusion = "directional_advantage"
        elif result.paired_mean_ci_95_high < 0:
            conclusion = "market_maker_advantage"
        else:
            conclusion = "inconclusive"
        cells.append(
            SensitivityCell(
                earnings_jump_volatility=level.quantize(FOUR_PLACES),
                mean_directional_minus_maker=result.mean_directional_minus_maker,
                paired_mean_ci_95_low=result.paired_mean_ci_95_low,
                paired_mean_ci_95_high=result.paired_mean_ci_95_high,
                market_maker_expected_shortfall_05=result.market_maker.expected_shortfall_05,
                directional_expected_shortfall_05=result.directional.expected_shortfall_05,
                conclusion=conclusion,
            )
        )
    conclusions = {cell.conclusion for cell in cells}
    return AgentSensitivityExperiment(
        trials_per_level=trials,
        base_seed=base_seed,
        cells=tuple(cells),
        stable_conclusion=len(conclusions) == 1,
    )
