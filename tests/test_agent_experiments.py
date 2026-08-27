from decimal import Decimal

from fastapi.testclient import TestClient

from volforge import EarningsScenario, RiskPreset, run_agent_comparison_experiment
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
    assert "profitability claim" in payload["interpretation"]
