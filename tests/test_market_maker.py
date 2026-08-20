from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from volforge import RiskPreset, quote_for_preset
from volforge.api import create_app


def test_quote_covers_fees_and_rounds_outward_to_ticks() -> None:
    quote = quote_for_preset(
        RiskPreset.BALANCED,
        theoretical_price=Decimal("2.50"),
        option_inventory=0,
        tick_size=Decimal("0.05"),
        base_half_spread=Decimal("0.10"),
        max_inventory_skew=Decimal("0.25"),
        per_contract_fee=Decimal("1.00"),
        contract_multiplier=100,
    )

    assert quote.effective_half_spread == Decimal("0.11")
    assert quote.bid_price == Decimal("2.35")
    assert quote.ask_price == Decimal("2.65")
    assert quote.bid_quantity == quote.ask_quantity == 5


def test_inventory_skew_encourages_risk_reduction_and_respects_limits() -> None:
    long_quote = quote_for_preset(
        RiskPreset.BALANCED,
        theoretical_price=Decimal("2.50"),
        option_inventory=25,
        max_inventory_skew=Decimal("0.25"),
    )
    short_quote = quote_for_preset(
        RiskPreset.BALANCED,
        theoretical_price=Decimal("2.50"),
        option_inventory=-25,
        max_inventory_skew=Decimal("0.25"),
    )

    assert long_quote.inventory_skew == Decimal("-0.25")
    assert long_quote.bid_quantity == 0
    assert short_quote.inventory_skew == Decimal("0.25")
    assert short_quote.ask_quantity == 0
    with pytest.raises(ValueError, match="exceeds"):
        quote_for_preset(
            RiskPreset.BALANCED,
            theoretical_price=Decimal("2.50"),
            option_inventory=26,
        )


def test_quote_policy_is_available_as_stateless_analysis(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "volforge.db"))
    response = client.post(
        "/v1/analysis/market-maker-quote",
        json={
            "theoretical_price": "2.50",
            "option_inventory": 20,
            "risk_preset": "balanced",
            "tick_size": "0.05",
            "base_half_spread": "0.10",
            "max_inventory_skew": "0.25",
            "per_contract_fee": "1.00",
        },
    )

    assert response.status_code == 200
    assert response.json()["storage"] == "stateless"
    assert Decimal(response.json()["inventory_skew"]) < 0
    assert response.json()["bid_quantity"] == 5
