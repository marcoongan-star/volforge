from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .contracts import Side
from .decisions import (
    ActionAnalysis,
    EarningsOutcome,
    TradeAction,
    analyze_earnings_actions,
    score_decision_for_preset,
)
from .risk import RiskPreset
from .session import TradingSession
from .store import SqliteSessionStore


PositiveDecimal = Annotated[Decimal, Field(gt=0)]
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


def _session_json(session_id: str, session: TradingSession) -> dict[str, object]:
    return {
        "session_id": session_id,
        "symbol": session.symbol,
        "tick_size": str(session.tick_size),
        "events": [
            {
                "sequence": event.sequence,
                "event_type": event.event_type.value,
                "data": event.data(),
            }
            for event in session.log.events
        ],
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

    return app


app = create_app()
