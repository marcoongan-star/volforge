from decimal import Decimal

import pytest

from volforge import EarningsScenario, RiskPreset, limits_for


def test_earnings_scenario_replays_from_seed() -> None:
    scenario = EarningsScenario()
    first = scenario.path(seed=8128, steps=20, earnings_step=10)
    replay = scenario.path(seed=8128, steps=20, earnings_step=10)
    different = scenario.path(seed=8129, steps=20, earnings_step=10)
    assert first == replay
    assert first != different
    assert len(first) == 21


def test_all_risk_presets_remain_bounded() -> None:
    cautious = limits_for(RiskPreset.CAUTIOUS)
    aggressive = limits_for(RiskPreset.AGGRESSIVE)
    assert cautious.max_order_quantity < aggressive.max_order_quantity
    assert aggressive.max_order_quantity <= 10
    assert aggressive.max_option_inventory <= 50

    with pytest.raises(ValueError, match="order quantity"):
        aggressive.validate_order(
            order_quantity=11,
            projected_inventory=11,
            projected_delta=200.0,
            current_pnl=Decimal("0"),
        )

