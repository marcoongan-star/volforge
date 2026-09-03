from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .agents import plan_directional_trade
from .agent_experiments import (
    AgentDistribution,
    plan_experiment_precision,
    plan_experiment_power,
    run_agent_comparison_experiment,
    run_agent_sensitivity_experiment,
)
from .contracts import Side
from .decisions import (
    ActionAnalysis,
    EarningsOutcome,
    TradeAction,
    analyze_earnings_actions,
    score_decision_for_preset,
)
from .risk import RiskPreset
from .ledger import AccountSnapshot
from .market_maker import quote_for_preset
from .session import SessionEvent, TradingSession
from .store import SqliteSessionStore
from .scenario import EarningsScenario


PositiveDecimal = Annotated[Decimal, Field(gt=0)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]


class OutcomeInput(BaseModel):
    label: str = Field(min_length=1)
    probability: Decimal = Field(ge=0, le=1)
    stock_return: Decimal = Field(gt=-1)


class EarningsAnalysisInput(BaseModel):
    outcomes: list[OutcomeInput] = Field(min_length=1)
    spot: PositiveDecimal
    strike: PositiveDecimal
    premium: Decimal = Field(ge=0)
    chosen_action: TradeAction
    risk_preset: RiskPreset = RiskPreset.BALANCED
    quantity: PositiveInt = 1
    contract_multiplier: PositiveInt = 100


class SessionCreateInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    tick_size: PositiveDecimal = Decimal("0.01")
    contract_multiplier: PositiveInt = 100


class ParticipantInput(BaseModel):
    participant_id: str = Field(min_length=1, max_length=100)
    starting_cash: Decimal = Decimal("0")


class OrderInput(BaseModel):
    order_id: str = Field(min_length=1, max_length=100)
    participant_id: str = Field(min_length=1, max_length=100)
    side: Side
    price: PositiveDecimal
    quantity: PositiveInt


class HedgeInput(BaseModel):
    participant_id: str = Field(min_length=1, max_length=100)
    option_delta: Decimal = Field(ge=-1, le=1)
    stock_price: PositiveDecimal
    per_share_fee: Decimal = Field(default=Decimal("0"), ge=0)
    fixed_fee: Decimal = Field(default=Decimal("0"), ge=0)


class MarketMakerQuoteInput(BaseModel):
    theoretical_price: PositiveDecimal
    option_inventory: int
    risk_preset: RiskPreset = RiskPreset.BALANCED
    tick_size: PositiveDecimal = Decimal("0.01")
    base_half_spread: Decimal = Field(default=Decimal("0.05"), ge=0)
    max_inventory_skew: Decimal = Field(default=Decimal("0.25"), ge=0)
    per_contract_fee: Decimal = Field(default=Decimal("0"), ge=0)
    contract_multiplier: PositiveInt = 100


class AgentComparisonInput(BaseModel):
    theoretical_price: PositiveDecimal
    forecast_price: PositiveDecimal
    confidence: Decimal = Field(ge=0, le=1)
    scenario_volatility: PositiveDecimal
    transaction_cost: Decimal = Field(default=Decimal("0.02"), ge=0)
    option_inventory: int = 0
    risk_preset: RiskPreset = RiskPreset.BALANCED
    tick_size: PositiveDecimal = Decimal("0.01")


class AgentExperimentInput(BaseModel):
    initial_spot: PositiveDecimal = Decimal("100")
    annual_volatility: Decimal = Field(default=Decimal("0.24"), ge=0)
    earnings_jump_volatility: Decimal = Field(default=Decimal("0.08"), ge=0)
    strike: PositiveDecimal = Decimal("100")
    forecast_option_price: PositiveDecimal
    confidence: Decimal = Field(ge=0, le=1)
    scenario_option_volatility: PositiveDecimal = Decimal("0.50")
    transaction_cost: Decimal = Field(default=Decimal("0.02"), ge=0)
    risk_preset: RiskPreset = RiskPreset.BALANCED
    trials: int = Field(default=500, ge=2, le=5000)
    base_seed: int = 14000
    target_mean_difference: PositiveDecimal = Decimal("250")
    target_detectable_difference: PositiveDecimal = Decimal("500")
    target_power: Decimal = Field(default=Decimal("0.80"), gt=Decimal("0.50"), lt=1)


class AgentSensitivityInput(BaseModel):
    initial_spot: PositiveDecimal = Decimal("100")
    annual_volatility: Decimal = Field(default=Decimal("0.24"), ge=0)
    earnings_jump_volatilities: list[NonNegativeDecimal] = Field(
        default_factory=lambda: [Decimal("0.04"), Decimal("0.08"), Decimal("0.12")],
        min_length=1,
        max_length=7,
    )
    strike: PositiveDecimal = Decimal("100")
    forecast_option_price: PositiveDecimal
    confidence: Decimal = Field(ge=0, le=1)
    scenario_option_volatility: PositiveDecimal = Decimal("0.50")
    transaction_cost: Decimal = Field(default=Decimal("0.02"), ge=0)
    risk_preset: RiskPreset = RiskPreset.BALANCED
    trials: int = Field(default=500, ge=2, le=5000)
    base_seed: int = 14000


def _analysis_json(analysis: ActionAnalysis) -> dict[str, object]:
    return {
        "action": analysis.action.value,
        "expected_pnl": str(analysis.expected_pnl),
        "pnl_standard_deviation": str(analysis.pnl_standard_deviation),
        "best_case_pnl": str(analysis.best_case_pnl),
        "worst_case_pnl": str(analysis.worst_case_pnl),
        "probability_of_profit": str(analysis.probability_of_profit),
        "outcome_pnls": [
            {"label": label, "pnl": str(pnl)} for label, pnl in analysis.outcome_pnls
        ],
    }


def _distribution_json(distribution: AgentDistribution) -> dict[str, str]:
    return {
        "mean_pnl": str(distribution.mean_pnl),
        "pnl_standard_deviation": str(distribution.pnl_standard_deviation),
        "probability_of_profit": str(distribution.probability_of_profit),
        "percentile_05": str(distribution.percentile_05),
        "expected_shortfall_05": str(distribution.expected_shortfall_05),
        "best_pnl": str(distribution.best_pnl),
        "worst_pnl": str(distribution.worst_pnl),
    }


def _session_json(session_id: str, session: TradingSession) -> dict[str, object]:
    return {
        "session_id": session_id,
        "symbol": session.symbol,
        "tick_size": str(session.tick_size),
        "events": [_event_json(event) for event in session.log.events],
        "active_orders": [
            {
                "order_id": order.order_id,
                "participant_id": order.participant_id,
                "side": order.side.value,
                "price": str(order.price),
                "quantity": order.quantity,
                "remaining": order.remaining,
                "sequence": order.sequence,
            }
            for order in session.active_orders()
        ],
    }


def _event_json(event: SessionEvent) -> dict[str, object]:
    return {
        "sequence": event.sequence,
        "event_type": event.event_type.value,
        "data": event.data(),
    }


def _account_json(account: AccountSnapshot) -> dict[str, object]:
    return {
        "participant_id": account.participant_id,
        "starting_cash": str(account.starting_cash),
        "cash": str(account.cash),
        "option_inventory": account.option_inventory,
        "option_mark": str(account.option_mark),
        "option_inventory_value": str(account.inventory_value),
        "stock_inventory": account.stock_inventory,
        "stock_mark": str(account.stock_mark),
        "stock_inventory_value": str(account.stock_inventory_value),
        "equity": str(account.equity),
        "pnl": str(account.pnl),
        "attribution": {
            "option_pnl": str(account.attribution.option_pnl),
            "hedge_pnl": str(account.attribution.hedge_pnl),
            "fees": str(account.attribution.fees),
            "total_pnl": str(account.attribution.total_pnl),
        },
    }


def create_app(database_path: str | Path | None = None) -> FastAPI:
    resolved_path = database_path or os.getenv("VOLFORGE_DATABASE_PATH", "volforge.db")
    store = SqliteSessionStore(resolved_path)
    app = FastAPI(
        title="VolForge API",
        version="0.2.0",
        description="Hybrid API: stateless quantitative analysis and durable exchange sessions.",
    )

    @app.post("/v1/analysis/earnings")
    def analyze_earnings(request: EarningsAnalysisInput) -> dict[str, object]:
        try:
            outcomes = tuple(
                EarningsOutcome(item.label, item.probability, item.stock_return)
                for item in request.outcomes
            )
            analyses = analyze_earnings_actions(
                outcomes,
                spot=request.spot,
                strike=request.strike,
                premium=request.premium,
                quantity=request.quantity,
                contract_multiplier=request.contract_multiplier,
            )
            scorecard = score_decision_for_preset(
                analyses, request.chosen_action, request.risk_preset
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "storage": "stateless",
            "risk_preset": request.risk_preset.value,
            "risk_aversion": str(scorecard.risk_aversion),
            "analyses": [_analysis_json(item) for item in analyses],
            "chosen_action": scorecard.chosen.analysis.action.value,
            "expected_value_benchmark": scorecard.expected_value_benchmark.action.value,
            "risk_adjusted_benchmark": scorecard.risk_adjusted_benchmark.analysis.action.value,
            "expected_value_opportunity_cost": str(
                scorecard.expected_value_opportunity_cost
            ),
            "risk_adjusted_opportunity_cost": str(
                scorecard.risk_adjusted_opportunity_cost
            ),
        }

    @app.post("/v1/analysis/market-maker-quote")
    def market_maker_quote(request: MarketMakerQuoteInput) -> dict[str, object]:
        try:
            plan = quote_for_preset(
                request.risk_preset,
                theoretical_price=request.theoretical_price,
                option_inventory=request.option_inventory,
                tick_size=request.tick_size,
                base_half_spread=request.base_half_spread,
                max_inventory_skew=request.max_inventory_skew,
                per_contract_fee=request.per_contract_fee,
                contract_multiplier=request.contract_multiplier,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "storage": "stateless",
            "risk_preset": request.risk_preset.value,
            "theoretical_price": str(plan.theoretical_price),
            "reservation_price": str(plan.reservation_price),
            "inventory_skew": str(plan.inventory_skew),
            "effective_half_spread": str(plan.effective_half_spread),
            "bid_price": str(plan.bid_price) if plan.bid_price is not None else None,
            "ask_price": str(plan.ask_price),
            "bid_quantity": plan.bid_quantity,
            "ask_quantity": plan.ask_quantity,
            "explanation": "Long inventory lowers both quotes; short inventory raises them. Fees widen the spread.",
        }

    @app.post("/v1/analysis/agents/compare")
    def compare_agents(request: AgentComparisonInput) -> dict[str, object]:
        try:
            maker = quote_for_preset(
                request.risk_preset,
                theoretical_price=request.theoretical_price,
                option_inventory=request.option_inventory,
                tick_size=request.tick_size,
                per_contract_fee=request.transaction_cost * Decimal("100"),
            )
            directional = plan_directional_trade(
                theoretical_price=request.theoretical_price,
                forecast_price=request.forecast_price,
                confidence=request.confidence,
                scenario_volatility=request.scenario_volatility,
                transaction_cost=request.transaction_cost,
                risk_preset=request.risk_preset,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "storage": "stateless",
            "risk_preset": request.risk_preset.value,
            "market_maker": {
                "objective": "earn spread while controlling inventory",
                "bid_price": str(maker.bid_price) if maker.bid_price is not None else None,
                "ask_price": str(maker.ask_price),
                "bid_quantity": maker.bid_quantity,
                "ask_quantity": maker.ask_quantity,
                "inventory_skew": str(maker.inventory_skew),
            },
            "directional": {
                "objective": "trade only when forecast edge clears costs and uncertainty",
                "action": directional.action.value,
                "quantity": directional.quantity,
                "raw_edge": str(directional.raw_edge),
                "confidence_weighted_edge": str(directional.confidence_weighted_edge),
                "risk_hurdle": str(directional.risk_hurdle),
                "edge_after_hurdle": str(directional.edge_after_hurdle),
            },
        }

    @app.post("/v1/experiments/agents")
    def compare_agent_distributions(
        request: AgentExperimentInput,
    ) -> dict[str, object]:
        try:
            result = run_agent_comparison_experiment(
                EarningsScenario(
                    initial_price=float(request.initial_spot),
                    annual_volatility=float(request.annual_volatility),
                    earnings_jump_volatility=float(request.earnings_jump_volatility),
                ),
                strike=request.strike,
                forecast_option_price=request.forecast_option_price,
                confidence=request.confidence,
                scenario_option_volatility=request.scenario_option_volatility,
                transaction_cost=request.transaction_cost,
                risk_preset=request.risk_preset,
                trials=request.trials,
                base_seed=request.base_seed,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        precision = plan_experiment_precision(
            paired_standard_deviation=result.paired_difference_standard_deviation,
            current_trials=result.trials,
            target_mean_difference=request.target_mean_difference,
        )
        power = plan_experiment_power(
            paired_standard_deviation=result.paired_difference_standard_deviation,
            current_trials=result.trials,
            target_detectable_difference=request.target_detectable_difference,
            target_power=request.target_power,
        )
        return {
            "data_status": "synthetic",
            "paired_paths": True,
            "trials": result.trials,
            "base_seed": result.base_seed,
            "directional_action": result.directional_action.value,
            "directional_quantity": result.directional_quantity,
            "market_maker": _distribution_json(result.market_maker),
            "directional": _distribution_json(result.directional),
            "mean_directional_minus_maker": str(
                result.mean_directional_minus_maker
            ),
            "paired_difference_standard_deviation": str(
                result.paired_difference_standard_deviation
            ),
            "paired_difference_standard_error": str(
                result.paired_difference_standard_error
            ),
            "unpaired_difference_standard_error": str(
                result.unpaired_difference_standard_error
            ),
            "paired_covariance": str(result.paired_covariance),
            "paired_correlation": str(result.paired_correlation),
            "common_random_number_efficiency": str(
                result.common_random_number_efficiency
            ),
            "precision_plan": {
                "target_mean_difference": str(precision.target_mean_difference),
                "confidence_multiplier": str(precision.confidence_multiplier),
                "current_margin_of_error": str(precision.current_margin_of_error),
                "required_trials": precision.required_trials,
                "additional_trials": precision.additional_trials,
                "target_reached": precision.target_reached,
            },
            "power_plan": {
                "target_detectable_difference": str(power.target_detectable_difference),
                "significance_level": str(power.significance_level),
                "target_power": str(power.target_power),
                "achieved_power": str(power.achieved_power),
                "required_trials": power.required_trials,
                "additional_trials": power.additional_trials,
                "target_reached": power.target_reached,
            },
            "paired_mean_ci_95": [
                str(result.paired_mean_ci_95_low),
                str(result.paired_mean_ci_95_high),
            ],
            "paired_standardized_effect": str(
                result.paired_standardized_effect
            ),
            "probability_directional_outperforms": str(
                result.probability_directional_outperforms
            ),
            "exact_sign_test": {
                "nonzero_pairs": result.nonzero_paired_trials,
                "directional_wins": result.directional_outperformance_count,
                "two_sided_p_value": str(result.exact_sign_test_p_value),
                "significant_at_05": result.exact_sign_test_significant_05,
                "null_hypothesis": "Each agent is equally likely to outperform on a non-tied paired path.",
            },
            "interpretation": "The mean interval and exact sign test answer different questions: average P&L difference versus path-by-path win frequency. The agents solve different objectives; this is a synthetic risk comparison, not a profitability claim.",
        }

    @app.post("/v1/experiments/agents/sensitivity")
    def compare_agent_sensitivity(
        request: AgentSensitivityInput,
    ) -> dict[str, object]:
        try:
            result = run_agent_sensitivity_experiment(
                initial_price=request.initial_spot,
                annual_volatility=request.annual_volatility,
                earnings_jump_volatilities=tuple(request.earnings_jump_volatilities),
                strike=request.strike,
                forecast_option_price=request.forecast_option_price,
                confidence=request.confidence,
                scenario_option_volatility=request.scenario_option_volatility,
                transaction_cost=request.transaction_cost,
                risk_preset=request.risk_preset,
                trials=request.trials,
                base_seed=request.base_seed,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {
            "data_status": "synthetic",
            "method": "paired common-random-number sensitivity grid",
            "trials_per_level": result.trials_per_level,
            "base_seed": result.base_seed,
            "stable_conclusion": result.stable_conclusion,
            "cells": [
                {
                    "earnings_jump_volatility": str(cell.earnings_jump_volatility),
                    "mean_directional_minus_maker": str(cell.mean_directional_minus_maker),
                    "paired_mean_ci_95": [
                        str(cell.paired_mean_ci_95_low),
                        str(cell.paired_mean_ci_95_high),
                    ],
                    "market_maker_expected_shortfall_05": str(
                        cell.market_maker_expected_shortfall_05
                    ),
                    "directional_expected_shortfall_05": str(
                        cell.directional_expected_shortfall_05
                    ),
                    "conclusion": cell.conclusion,
                }
                for cell in result.cells
            ],
            "interpretation": "A stable label means the statistical conclusion survived only the tested synthetic volatility assumptions; it is not a live-performance claim.",
        }

    @app.post("/v1/sessions", status_code=201)
    def create_session(request: SessionCreateInput) -> dict[str, object]:
        session_id = str(uuid4())
        try:
            session = store.create_session(
                session_id,
                request.symbol.upper(),
                tick_size=request.tick_size,
                contract_multiplier=request.contract_multiplier,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _session_json(session_id, session)

    @app.get("/v1/sessions/{session_id}")
    def get_session(session_id: str) -> dict[str, object]:
        try:
            return _session_json(session_id, store.load(session_id))
        except KeyError as error:
            raise HTTPException(status_code=404, detail="session not found") from error

    @app.get("/v1/sessions/{session_id}/events")
    def session_events(
        session_id: str,
        after_sequence: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> dict[str, object]:
        """Return the canonical event suffix used after a client reconnects."""
        try:
            recovery_page = store.events_after(
                session_id, after_sequence=after_sequence, limit=limit + 1
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="session not found") from error
        delivered = recovery_page[:limit]
        next_sequence = delivered[-1].sequence if delivered else after_sequence
        return {
            "session_id": session_id,
            "after_sequence": after_sequence,
            "next_sequence": next_sequence,
            "has_more": len(recovery_page) > limit,
            "events": [_event_json(event) for event in delivered],
            "recovery_rule": "Replace or append only contiguous server events after the last confirmed sequence.",
        }

    @app.post("/v1/sessions/{session_id}/participants")
    def register_participant(
        session_id: str, request: ParticipantInput
    ) -> dict[str, object]:
        try:
            session = store.mutate(
                session_id,
                lambda current: current.register_participant(
                    request.participant_id, request.starting_cash
                ),
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="session not found") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return _session_json(session_id, session)

    @app.post("/v1/sessions/{session_id}/orders")
    def submit_order(session_id: str, request: OrderInput) -> dict[str, object]:
        try:
            session = store.mutate(
                session_id,
                lambda current: current.submit_order(
                    order_id=request.order_id,
                    participant_id=request.participant_id,
                    side=request.side,
                    price=request.price,
                    quantity=request.quantity,
                ),
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="session not found") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return _session_json(session_id, session)

    @app.post("/v1/sessions/{session_id}/hedges")
    def rebalance_session_delta(
        session_id: str, request: HedgeInput
    ) -> dict[str, object]:
        try:
            session = store.mutate(
                session_id,
                lambda current: current.rebalance_delta(
                    request.participant_id,
                    option_delta=request.option_delta,
                    stock_price=request.stock_price,
                    per_share_fee=request.per_share_fee,
                    fixed_fee=request.fixed_fee,
                ),
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="session not found") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {
            "session": _session_json(session_id, session),
            "account": _account_json(
                session.account(
                    request.participant_id,
                    option_mark=Decimal("0"),
                    stock_mark=request.stock_price,
                )
            ),
        }

    @app.get("/v1/sessions/{session_id}/accounts/{participant_id}")
    def session_account(
        session_id: str,
        participant_id: str,
        option_mark: Decimal,
        stock_mark: Decimal = Decimal("0"),
    ) -> dict[str, object]:
        try:
            session = store.load(session_id)
            return _account_json(session.account(participant_id, option_mark, stock_mark))
        except KeyError as error:
            raise HTTPException(status_code=404, detail="session not found") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.websocket("/v1/sessions/{session_id}/stream")
    async def session_stream(
        websocket: WebSocket,
        session_id: str,
        after_sequence: int = Query(default=0, ge=0),
    ) -> None:
        """Notify clients that durable events are available after their cursor."""
        try:
            store.metadata(session_id)
        except KeyError:
            await websocket.close(code=4404, reason="session not found")
            return

        await websocket.accept()
        cursor = after_sequence
        await websocket.send_json(
            {
                "type": "stream.ready",
                "session_id": session_id,
                "after_sequence": cursor,
                "recovery_url": f"/v1/sessions/{session_id}/events?after_sequence={cursor}",
            }
        )
        try:
            while True:
                available = store.events_after(
                    session_id, after_sequence=cursor, limit=101
                )
                if available:
                    next_sequence = available[-1].sequence
                    await websocket.send_json(
                        {
                            "type": "events.available",
                            "session_id": session_id,
                            "after_sequence": cursor,
                            "next_sequence": next_sequence,
                            "event_count": len(available),
                            "has_more": len(available) == 101,
                            "recovery_url": (
                                f"/v1/sessions/{session_id}/events"
                                f"?after_sequence={cursor}"
                            ),
                        }
                    )
                    cursor = next_sequence
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(), timeout=0.25
                    )
                except TimeoutError:
                    continue
                if message == "ping":
                    await websocket.send_json(
                        {"type": "pong", "confirmed_sequence": cursor}
                    )
        except WebSocketDisconnect:
            return

    return app


app = create_app()
