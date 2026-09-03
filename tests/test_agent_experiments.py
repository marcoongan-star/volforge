from decimal import Decimal

from fastapi.testclient import TestClient

from volforge import (
    EarningsScenario,
    RiskPreset,
    plan_experiment_precision,
    plan_experiment_power,
    run_agent_comparison_experiment,
    run_agent_sensitivity_experiment,
)
from volforge.api import create_app


def inputs() -> dict[str, object]:
    return {
        "strike": Decimal("100"),
        "forecast_option_price": Decimal("6.00"),
        "confidence": Decimal("0.85"),
        "scenario_option_volatility": Decimal("0.50"),
        "transaction_cost": Decimal("0.02"),
        "risk_preset": RiskPreset.BALANCED,
        "trials": 300,
        "base_seed": 14000,
    }


def test_paired_agent_experiment_is_replayable_and_reports_downside() -> None:
    scenario = EarningsScenario(annual_volatility=0.24, earnings_jump_volatility=0.08)
    first = run_agent_comparison_experiment(scenario, **inputs())
    replay = run_agent_comparison_experiment(scenario, **inputs())

    assert first == replay
    assert first.market_maker.worst_pnl <= first.market_maker.percentile_05
    assert first.market_maker.expected_shortfall_05 <= first.market_maker.percentile_05
    assert first.directional.worst_pnl <= first.directional.percentile_05
    assert Decimal("0") <= first.probability_directional_outperforms <= Decimal("1")
    assert first.paired_mean_ci_95_low <= first.mean_directional_minus_maker
    assert first.paired_mean_ci_95_high >= first.mean_directional_minus_maker
    assert first.paired_difference_standard_error < first.paired_difference_standard_deviation
    assert Decimal("-1") <= first.paired_correlation <= Decimal("1")
    assert first.unpaired_difference_standard_error > 0
    assert first.common_random_number_efficiency > 0
    assert first.nonzero_paired_trials <= first.trials
    assert first.directional_outperformance_count <= first.nonzero_paired_trials
    assert Decimal("0") <= first.exact_sign_test_p_value <= Decimal("1")
    assert first.exact_sign_test_significant_05 is (
        first.exact_sign_test_p_value <= Decimal("0.05")
    )
    expected_efficiency = (
        first.unpaired_difference_standard_error
        / first.paired_difference_standard_error
    ).quantize(Decimal("0.0001"))
    assert abs(first.common_random_number_efficiency - expected_efficiency) <= Decimal("0.0001")


def test_precision_plan_converts_uncertainty_into_required_paths() -> None:
    plan = plan_experiment_precision(
        paired_standard_deviation=Decimal("100"),
        current_trials=100,
        target_mean_difference=Decimal("10"),
    )
    reached = plan_experiment_precision(
        paired_standard_deviation=Decimal("100"),
        current_trials=100,
        target_mean_difference=Decimal("20"),
    )

    assert plan.current_margin_of_error == Decimal("19.60")
    assert plan.required_trials == 385
    assert plan.additional_trials == 285
    assert plan.target_reached is False
    assert reached.required_trials == 97
    assert reached.additional_trials == 0
    assert reached.target_reached is True


def test_power_plan_sizes_a_two_sided_paired_experiment() -> None:
    plan = plan_experiment_power(
        paired_standard_deviation=Decimal("100"),
        current_trials=20,
        target_detectable_difference=Decimal("50"),
    )
    larger_effect = plan_experiment_power(
        paired_standard_deviation=Decimal("100"),
        current_trials=20,
        target_detectable_difference=Decimal("80"),
    )

    assert plan.required_trials == 32
    assert plan.additional_trials == 12
    assert Decimal("0.5") < plan.achieved_power < Decimal("0.8")
    assert plan.target_reached is False
    assert larger_effect.required_trials < plan.required_trials
    assert larger_effect.target_reached is True


def test_power_plan_rejects_degenerate_or_invalid_assumptions() -> None:
    for kwargs in (
        {"paired_standard_deviation": Decimal("0")},
        {"target_detectable_difference": Decimal("0")},
        {"significance_level": Decimal("1")},
        {"target_power": Decimal("0.5")},
    ):
        inputs = {
            "paired_standard_deviation": Decimal("100"),
            "current_trials": 20,
            "target_detectable_difference": Decimal("50"),
            **kwargs,
        }
        try:
            plan_experiment_power(**inputs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid power assumptions should be rejected")


def test_low_confidence_directional_agent_stays_flat_on_every_path() -> None:
    result = run_agent_comparison_experiment(
        EarningsScenario(),
        **{
            **inputs(),
            "forecast_option_price": Decimal("5.50"),
            "confidence": Decimal("0.10"),
            "risk_preset": RiskPreset.CAUTIOUS,
        },
    )

    assert result.directional_action.value == "hold"
    assert result.directional_quantity == 0
    assert result.directional.mean_pnl == Decimal("0.00")
    assert result.directional.pnl_standard_deviation == Decimal("0.00")


def test_agent_experiment_api_labels_paired_synthetic_paths(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "volforge.db"))
    response = client.post(
        "/v1/experiments/agents",
        json={
            "initial_spot": "100",
            "strike": "100",
            "forecast_option_price": "6.00",
            "confidence": "0.85",
            "trials": 100,
            "base_seed": 14000,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "synthetic"
    assert payload["paired_paths"] is True
    assert payload["trials"] == 100
    assert "expected_shortfall_05" in payload["market_maker"]
    assert "expected_shortfall_05" in payload["directional"]
    assert len(payload["paired_mean_ci_95"]) == 2
    assert "paired_difference_standard_error" in payload
    assert "paired_standardized_effect" in payload
    assert "unpaired_difference_standard_error" in payload
    assert "paired_covariance" in payload
    assert "paired_correlation" in payload
    assert "common_random_number_efficiency" in payload
    assert payload["exact_sign_test"]["nonzero_pairs"] <= payload["trials"]
    assert payload["exact_sign_test"]["directional_wins"] <= payload["exact_sign_test"]["nonzero_pairs"]
    assert 0 <= float(payload["exact_sign_test"]["two_sided_p_value"]) <= 1
    assert "equally likely" in payload["exact_sign_test"]["null_hypothesis"]
    assert payload["precision_plan"]["required_trials"] >= 2
    assert payload["precision_plan"]["additional_trials"] >= 0
    assert payload["precision_plan"]["target_mean_difference"] == "250.00"
    assert payload["power_plan"]["target_detectable_difference"] == "500.00"
    assert payload["power_plan"]["target_power"] == "0.8000"
    assert payload["power_plan"]["required_trials"] >= 2
    assert "profitability claim" in payload["interpretation"]


def test_volatility_sensitivity_is_replayable_and_classifies_intervals() -> None:
    request = {
        "initial_price": Decimal("100"),
        "annual_volatility": Decimal("0.24"),
        "earnings_jump_volatilities": (
            Decimal("0.12"),
            Decimal("0.04"),
            Decimal("0.08"),
        ),
        **inputs(),
    }

    first = run_agent_sensitivity_experiment(**request)
    replay = run_agent_sensitivity_experiment(**request)

    assert first == replay
    assert [cell.earnings_jump_volatility for cell in first.cells] == [
        Decimal("0.0400"),
        Decimal("0.0800"),
        Decimal("0.1200"),
    ]
    for cell in first.cells:
        expected = (
            "directional_advantage"
            if cell.paired_mean_ci_95_low > 0
            else "market_maker_advantage"
            if cell.paired_mean_ci_95_high < 0
            else "inconclusive"
        )
        assert cell.conclusion == expected
    assert first.stable_conclusion is (
        len({cell.conclusion for cell in first.cells}) == 1
    )


def test_sensitivity_rejects_duplicate_assumptions() -> None:
    try:
        run_agent_sensitivity_experiment(
            initial_price=Decimal("100"),
            annual_volatility=Decimal("0.24"),
            earnings_jump_volatilities=(Decimal("0.08"), Decimal("0.08")),
            **inputs(),
        )
    except ValueError as error:
        assert "unique" in str(error)
    else:
        raise AssertionError("duplicate assumptions should be rejected")


def test_agent_sensitivity_api_labels_synthetic_common_paths(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "volforge.db"))
    response = client.post(
        "/v1/experiments/agents/sensitivity",
        json={
            "forecast_option_price": "6.00",
            "confidence": "0.85",
            "trials": 100,
            "earnings_jump_volatilities": ["0.04", "0.08", "0.12"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "synthetic"
    assert payload["method"] == "paired common-random-number sensitivity grid"
    assert payload["trials_per_level"] == 100
    assert len(payload["cells"]) == 3
    assert all(len(cell["paired_mean_ci_95"]) == 2 for cell in payload["cells"])
    assert {cell["conclusion"] for cell in payload["cells"]} <= {
        "directional_advantage",
        "market_maker_advantage",
        "inconclusive",
    }
