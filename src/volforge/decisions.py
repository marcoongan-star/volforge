from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum


CENT = Decimal("0.01")


class TradeAction(StrEnum):
    BUY_CALL = "buy_call"
    SELL_CALL = "sell_call"
    STAY_FLAT = "stay_flat"


@dataclass(frozen=True)
class EarningsOutcome:
    label: str
    probability: Decimal
    stock_return: Decimal

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("outcome label cannot be empty")
        if not Decimal("0") <= self.probability <= Decimal("1"):
            raise ValueError("outcome probability must be between zero and one")
        if self.stock_return <= Decimal("-1"):
            raise ValueError("stock return cannot imply a negative terminal price")


@dataclass(frozen=True)
class ActionAnalysis:
    action: TradeAction
    expected_pnl: Decimal
    best_case_pnl: Decimal
    worst_case_pnl: Decimal
    probability_of_profit: Decimal
    outcome_pnls: tuple[tuple[str, Decimal], ...]


@dataclass(frozen=True)
class DecisionReview:
    chosen: ActionAnalysis
    benchmark: ActionAnalysis
    opportunity_cost: Decimal

    @property
    def is_expected_value_optimal(self) -> bool:
        return self.opportunity_cost == 0


def _validate_inputs(
    outcomes: tuple[EarningsOutcome, ...],
    *,
    spot: Decimal,
    strike: Decimal,
    premium: Decimal,
    quantity: int,
    contract_multiplier: int,
) -> None:
    if not outcomes:
        raise ValueError("at least one earnings outcome is required")
    if sum((outcome.probability for outcome in outcomes), start=Decimal("0")) != Decimal("1"):
        raise ValueError("outcome probabilities must sum to one")
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if premium < 0:
        raise ValueError("premium cannot be negative")
    if quantity <= 0 or contract_multiplier <= 0:
        raise ValueError("quantity and contract multiplier must be positive")


def analyze_earnings_actions(
    outcomes: tuple[EarningsOutcome, ...],
    *,
    spot: Decimal,
    strike: Decimal,
    premium: Decimal,
    quantity: int = 1,
    contract_multiplier: int = 100,
) -> tuple[ActionAnalysis, ...]:
    """Compare call decisions under a user's explicit discrete earnings beliefs."""
    _validate_inputs(
        outcomes,
        spot=spot,
        strike=strike,
        premium=premium,
        quantity=quantity,
        contract_multiplier=contract_multiplier,
    )
    scale = Decimal(quantity * contract_multiplier)
    analyses: list[ActionAnalysis] = []
    for action in TradeAction:
        outcome_pnls: list[tuple[str, Decimal]] = []
        expected_pnl = Decimal("0")
        probability_of_profit = Decimal("0")
        for outcome in outcomes:
            terminal_spot = spot * (Decimal("1") + outcome.stock_return)
            call_payoff = max(Decimal("0"), terminal_spot - strike)
            long_pnl = (call_payoff - premium) * scale
            if action is TradeAction.BUY_CALL:
                pnl = long_pnl
            elif action is TradeAction.SELL_CALL:
                pnl = -long_pnl
            else:
                pnl = Decimal("0")
            pnl = pnl.quantize(CENT, rounding=ROUND_HALF_UP)
            outcome_pnls.append((outcome.label, pnl))
            expected_pnl += outcome.probability * pnl
            if pnl > 0:
                probability_of_profit += outcome.probability

        pnl_values = [pnl for _, pnl in outcome_pnls]
        analyses.append(
            ActionAnalysis(
                action=action,
                expected_pnl=expected_pnl.quantize(CENT, rounding=ROUND_HALF_UP),
                best_case_pnl=max(pnl_values),
                worst_case_pnl=min(pnl_values),
                probability_of_profit=probability_of_profit,
                outcome_pnls=tuple(outcome_pnls),
            )
        )
    return tuple(analyses)


def review_decision(
    analyses: tuple[ActionAnalysis, ...], chosen_action: TradeAction
) -> DecisionReview:
    if {analysis.action for analysis in analyses} != set(TradeAction):
        raise ValueError("analysis must contain each trade action exactly once")
    by_action = {analysis.action: analysis for analysis in analyses}
    # STAY_FLAT wins an exact tie: no risk is preferred without extra expected return.
    benchmark = max(
        analyses,
        key=lambda analysis: (
            analysis.expected_pnl,
            analysis.action is TradeAction.STAY_FLAT,
        ),
    )
    chosen = by_action[chosen_action]
    return DecisionReview(
        chosen=chosen,
        benchmark=benchmark,
        opportunity_cost=benchmark.expected_pnl - chosen.expected_pnl,
    )
