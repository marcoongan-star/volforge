from decimal import Decimal

from fastapi.testclient import TestClient

from volforge import DirectionalAction, RiskPreset, plan_directional_trade
from volforge.api import create_app


def test_directional_agent_holds_when_uncertain_edge_does_not_clear_hurdle() -> None:
    plan = plan_directional_trade(
        theoretical_price=Decimal("4.25"),
        forecast_price=Decimal("4.40"),
        confidence=Decimal("0.40"),
        scenario_volatility=Decimal("0.50"),
        transaction_cost=Decimal("0.02"),
        risk_preset=RiskPreset.CAUTIOUS,
    )

    assert plan.action is DirectionalAction.HOLD
    assert plan.quantity == 0
    assert plan.edge_after_hurdle < 0


def test_directional_agent_sizes_strong_edge_with_preset_limit() -> None:
    plan = plan_directional_trade(
        theoretical_price=Decimal("4.25"),
        forecast_price=Decimal("5.00"),
        confidence=Decimal("0.90"),
        scenario_volatility=Decimal("0.50"),
        transaction_cost=Decimal("0.02"),
        risk_preset=RiskPreset.BALANCED,
    )

    assert plan.action is DirectionalAction.BUY
    assert 1 <= plan.quantity <= 5
    assert plan.edge_after_hurdle > 0


def test_agent_comparison_exposes_different_objectives(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "volforge.db"))
    response = client.post(
        "/v1/analysis/agents/compare",
        json={
            "theoretical_price": "4.25",
            "forecast_price": "5.00",
            "confidence": "0.90",
            "scenario_volatility": "0.50",
            "transaction_cost": "0.02",
            "option_inventory": -5,
            "risk_preset": "balanced",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["storage"] == "stateless"
    assert payload["market_maker"]["inventory_skew"] != "0.00"
    assert payload["directional"]["action"] == "buy"
    assert Decimal(payload["directional"]["edge_after_hurdle"]) == Decimal("0.625")
