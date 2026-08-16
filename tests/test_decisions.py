from decimal import Decimal

import pytest

from volforge import (
    EarningsOutcome,
    RiskPreset,
    TradeAction,
    analyze_earnings_actions,
    review_decision,
    score_decision,
    score_decision_for_preset,
)


def beliefs() -> tuple[EarningsOutcome, ...]:
    return (
        EarningsOutcome("miss", Decimal("0.40"), Decimal("-0.10")),
        EarningsOutcome("beat", Decimal("0.60"), Decimal("0.20")),
    )


def test_expected_value_is_probability_weighted_not_win_rate() -> None:
    analyses = analyze_earnings_actions(
        beliefs(), spot=Decimal("100"), strike=Decimal("100"), premium=Decimal("5")
    )
    calls = {analysis.action: analysis for analysis in analyses}

    assert calls[TradeAction.BUY_CALL].expected_pnl == Decimal("700.00")
    assert calls[TradeAction.BUY_CALL].pnl_standard_deviation == Decimal("979.80")
    assert calls[TradeAction.BUY_CALL].probability_of_profit == Decimal("0.60")
    assert calls[TradeAction.BUY_CALL].worst_case_pnl == Decimal("-500.00")
    assert calls[TradeAction.SELL_CALL].expected_pnl == Decimal("-700.00")
    assert calls[TradeAction.STAY_FLAT].expected_pnl == Decimal("0.00")
    assert calls[TradeAction.STAY_FLAT].pnl_standard_deviation == Decimal("0.00")


def test_review_separates_decision_quality_from_realized_outcome() -> None:
    analyses = analyze_earnings_actions(
        beliefs(), spot=Decimal("100"), strike=Decimal("100"), premium=Decimal("5")
    )
    review = review_decision(analyses, TradeAction.STAY_FLAT)

    assert review.benchmark.action is TradeAction.BUY_CALL
    assert review.opportunity_cost == Decimal("700.00")
    assert not review.is_expected_value_optimal


def test_probabilities_must_describe_a_complete_distribution() -> None:
    incomplete = (EarningsOutcome("beat", Decimal("0.60"), Decimal("0.20")),)
    with pytest.raises(ValueError, match="sum to one"):
        analyze_earnings_actions(
            incomplete,
            spot=Decimal("100"),
            strike=Decimal("100"),
            premium=Decimal("5"),
        )


def test_expected_value_and_cautious_benchmarks_can_disagree() -> None:
    analyses = analyze_earnings_actions(
        beliefs(), spot=Decimal("100"), strike=Decimal("100"), premium=Decimal("5")
    )
    scorecard = score_decision_for_preset(
        analyses, TradeAction.BUY_CALL, RiskPreset.CAUTIOUS
    )

    assert scorecard.expected_value_benchmark.action is TradeAction.BUY_CALL
    assert scorecard.risk_adjusted_benchmark.analysis.action is TradeAction.STAY_FLAT
    assert scorecard.expected_value_opportunity_cost == Decimal("0.00")
    assert scorecard.risk_adjusted_opportunity_cost > 0


def test_aggressive_preset_accepts_dispersion_for_expected_return() -> None:
    analyses = analyze_earnings_actions(
        beliefs(), spot=Decimal("100"), strike=Decimal("100"), premium=Decimal("5")
    )
    scorecard = score_decision_for_preset(
        analyses, TradeAction.BUY_CALL, RiskPreset.AGGRESSIVE
    )
    assert scorecard.risk_adjusted_benchmark.analysis.action is TradeAction.BUY_CALL
    assert scorecard.chosen.risk_adjusted_score == Decimal("602.02")


def test_risk_aversion_cannot_reward_more_risk() -> None:
    analyses = analyze_earnings_actions(
        beliefs(), spot=Decimal("100"), strike=Decimal("100"), premium=Decimal("5")
    )
    with pytest.raises(ValueError, match="cannot be negative"):
        score_decision(
            analyses,
            TradeAction.BUY_CALL,
            risk_aversion=Decimal("-0.1"),
        )
