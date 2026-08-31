from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from math import ceil, sqrt
from statistics import NormalDist

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


@dataclass(frozen=True)
class ExperimentPrecisionPlan:
    current_trials: int
    target_mean_difference: Decimal
    confidence_multiplier: Decimal
    current_margin_of_error: Decimal
    required_trials: int
    additional_trials: int
    target_reached: bool


@dataclass(frozen=True)
class ExperimentPowerPlan:
    current_trials: int
    target_detectable_difference: Decimal
    significance_level: Decimal
    target_power: Decimal
    achieved_power: Decimal
    required_trials: int
    additional_trials: int
    target_reached: bool


def plan_experiment_power(
    *,
    paired_standard_deviation: Decimal,
    current_trials: int,
    target_detectable_difference: Decimal,
    significance_level: Decimal = Decimal("0.05"),
    target_power: Decimal = Decimal("0.80"),
) -> ExperimentPowerPlan:
    """Plan a two-sided paired normal-approximation test before more paths run."""
    if paired_standard_deviation <= 0:
        raise ValueError("paired standard deviation must be positive")
    if current_trials < 2:
        raise ValueError("at least two current trials are required")
    if target_detectable_difference <= 0:
        raise ValueError("target detectable difference must be positive")
    if not Decimal("0") < significance_level < Decimal("1"):
        raise ValueError("significance level must be between zero and one")
    if not Decimal("0.5") < target_power < Decimal("1"):
        raise ValueError("target power must be between 0.5 and one")

    normal = NormalDist()
    alpha = float(significance_level)
    desired_power = float(target_power)
    standard_deviation = float(paired_standard_deviation)
    detectable_difference = float(target_detectable_difference)
    critical_value = normal.inv_cdf(1 - alpha / 2)
    power_value = normal.inv_cdf(desired_power)
    required = max(
        2,
        ceil(
            ((critical_value + power_value) * standard_deviation / detectable_difference)
            ** 2
        ),
    )
    noncentral_shift = sqrt(current_trials) * detectable_difference / standard_deviation
    achieved = normal.cdf(noncentral_shift - critical_value) + normal.cdf(
        -noncentral_shift - critical_value
    )
    achieved_decimal = Decimal(str(achieved)).quantize(
        FOUR_PLACES, rounding=ROUND_HALF_UP
    )
    return ExperimentPowerPlan(
        current_trials=current_trials,
        target_detectable_difference=target_detectable_difference.quantize(
            CENT, rounding=ROUND_HALF_UP
        ),
        significance_level=significance_level.quantize(FOUR_PLACES),
        target_power=target_power.quantize(FOUR_PLACES),
        achieved_power=achieved_decimal,
        required_trials=required,
        additional_trials=max(0, required - current_trials),
        target_reached=achieved_decimal >= target_power,
    )


def plan_experiment_precision(
    *,
    paired_standard_deviation: Decimal,
    current_trials: int,
    target_mean_difference: Decimal,
    confidence_multiplier: Decimal = Decimal("1.96"),
) -> ExperimentPrecisionPlan:
    """Estimate paths needed for a 95% CI half-width no larger than the target."""
    if paired_standard_deviation < 0:
        raise ValueError("paired standard deviation cannot be negative")
    if current_trials < 2:
        raise ValueError("at least two current trials are required")
    if target_mean_difference <= 0 or confidence_multiplier <= 0:
        raise ValueError("target difference and confidence multiplier must be positive")

    current_margin = (
        confidence_multiplier
        * paired_standard_deviation
        / Decimal(current_trials).sqrt()
    )
    required_decimal = (
        confidence_multiplier
        * paired_standard_deviation
        / target_mean_difference
    ) ** 2
    required = max(2, int(required_decimal.to_integral_value(rounding=ROUND_CEILING)))
    return ExperimentPrecisionPlan(
        current_trials=current_trials,
        target_mean_difference=target_mean_difference.quantize(CENT, rounding=ROUND_HALF_UP),
        confidence_multiplier=confidence_multiplier.quantize(FOUR_PLACES),
        current_margin_of_error=current_margin.quantize(CENT, rounding=ROUND_HALF_UP),
        required_trials=required,
        additional_trials=max(0, required - current_trials),
        target_reached=current_trials >= required,
    )


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
