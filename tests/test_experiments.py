from decimal import Decimal

from volforge import EarningsScenario, run_long_straddle_experiment


def test_straddle_experiment_replays_with_confidence_interval() -> None:
    scenario = EarningsScenario(annual_volatility=0.20, earnings_jump_volatility=0.10)
    inputs = {
        "strike": Decimal("100"),
        "total_premium": Decimal("8"),
        "trials": 250,
        "base_seed": 5000,
    }
    first = run_long_straddle_experiment(scenario, **inputs)
    replay = run_long_straddle_experiment(scenario, **inputs)

    assert first == replay
    assert first.confidence_interval_95[0] <= first.mean_pnl <= first.confidence_interval_95[1]
    assert Decimal("0") <= first.probability_of_profit <= Decimal("1")
    assert first.best_pnl >= first.worst_pnl


def test_higher_premium_reduces_every_straddle_result() -> None:
    scenario = EarningsScenario(annual_volatility=0.20, earnings_jump_volatility=0.10)
    common = {"strike": Decimal("100"), "trials": 100, "base_seed": 9000}
    cheaper = run_long_straddle_experiment(scenario, total_premium=Decimal("6"), **common)
    dearer = run_long_straddle_experiment(scenario, total_premium=Decimal("8"), **common)

    assert cheaper.mean_pnl - dearer.mean_pnl == Decimal("200.00")
    assert cheaper.best_pnl - dearer.best_pnl == Decimal("200.00")
    assert cheaper.worst_pnl - dearer.worst_pnl == Decimal("200.00")
    assert cheaper.probability_of_profit >= dearer.probability_of_profit


def test_no_movement_loses_exactly_the_paid_premium() -> None:
    scenario = EarningsScenario(annual_volatility=0, earnings_jump_volatility=0)
    result = run_long_straddle_experiment(
        scenario,
        strike=Decimal("100"),
        total_premium=Decimal("5"),
        trials=2,
        base_seed=1,
    )

    assert result.mean_pnl == Decimal("-500.00")
    assert result.pnl_standard_deviation == Decimal("0.00")
    assert result.probability_of_profit == Decimal("0.0000")
