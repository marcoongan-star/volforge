from decimal import Decimal

import pytest

from volforge import Side, TradingSession


def traded_session() -> TradingSession:
    session = TradingSession("WIRTZ-C100")
    session.register_participant("market-maker", Decimal("10000"))
    session.register_participant("directional-trader", Decimal("10000"))
    session.submit_order(
        order_id="ask-1",
        participant_id="market-maker",
        side=Side.SELL,
        price=Decimal("2.10"),
        quantity=3,
    )
    session.submit_order(
        order_id="buy-1",
        participant_id="directional-trader",
        side=Side.BUY,
        price=Decimal("2.10"),
        quantity=2,
    )
    return session


def test_fill_conserves_cash_and_option_inventory() -> None:
    session = traded_session()
    maker = session.account("market-maker", Decimal("2.10"))
    trader = session.account("directional-trader", Decimal("2.10"))

    assert maker.cash == Decimal("10420.00")
    assert trader.cash == Decimal("9580.00")
    assert maker.option_inventory == -2
    assert trader.option_inventory == 2
    assert maker.cash + trader.cash == Decimal("20000.00")
    assert maker.option_inventory + trader.option_inventory == 0
    assert maker.pnl == trader.pnl == Decimal("0.00")


def test_mark_to_market_pnl_is_zero_sum_between_counterparties() -> None:
    session = traded_session()
    maker = session.account("market-maker", Decimal("2.50"))
    trader = session.account("directional-trader", Decimal("2.50"))

    assert maker.pnl == Decimal("-80.00")
    assert trader.pnl == Decimal("80.00")
    assert maker.pnl + trader.pnl == 0


def test_registered_cash_and_ledger_replay_with_the_session() -> None:
    session = traded_session()
    replay = TradingSession.replay(symbol=session.symbol, events=session.log.events)

    assert replay.log.events == session.log.events
    assert replay.account("market-maker", Decimal("2.50")) == session.account(
        "market-maker", Decimal("2.50")
    )
    assert replay.account("directional-trader", Decimal("2.50")) == session.account(
        "directional-trader", Decimal("2.50")
    )


def test_negative_option_mark_is_rejected() -> None:
    session = traded_session()
    with pytest.raises(ValueError, match="option_mark"):
        session.account("market-maker", Decimal("-0.01"))
