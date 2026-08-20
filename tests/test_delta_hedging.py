from decimal import Decimal

from volforge import Side, TradingSession


def _short_call_session() -> TradingSession:
    session = TradingSession("WIRTZ-C100")
    session.register_participant("market-maker", Decimal("10000"))
    session.register_participant("directional-trader", Decimal("10000"))
    session.submit_order(
        order_id="maker-ask",
        participant_id="market-maker",
        side=Side.SELL,
        price=Decimal("2.10"),
        quantity=2,
    )
    session.submit_order(
        order_id="trader-buy",
        participant_id="directional-trader",
        side=Side.BUY,
        price=Decimal("2.10"),
        quantity=2,
    )
    return session


def test_delta_target_and_pnl_attribution_reconcile_to_equity() -> None:
    session = _short_call_session()

    trade = session.ledger.rebalance_delta(
        "market-maker",
        option_delta=Decimal("0.60"),
        stock_price=Decimal("100"),
        per_share_fee=Decimal("0.01"),
        fixed_fee=Decimal("0.50"),
    )
    assert trade is not None
    assert trade.quantity == 120
    assert trade.fee == Decimal("1.70")

    account = session.ledger.snapshot(
        "market-maker", option_mark=Decimal("2.50"), stock_mark=Decimal("105")
    )
    assert account.attribution.option_pnl == Decimal("-80.00")
    assert account.attribution.hedge_pnl == Decimal("600")
    assert account.attribution.fees == Decimal("1.70")
    assert account.attribution.total_pnl == Decimal("518.30")
    assert account.pnl == account.attribution.total_pnl


def test_rehedge_trades_only_the_change_in_target_delta() -> None:
    session = _short_call_session()
    session.ledger.rebalance_delta(
        "market-maker",
        option_delta=Decimal("0.60"),
        stock_price=Decimal("100"),
        per_share_fee=Decimal("0.01"),
        fixed_fee=Decimal("0.50"),
    )

    trade = session.ledger.rebalance_delta(
        "market-maker",
        option_delta=Decimal("0.40"),
        stock_price=Decimal("105"),
        per_share_fee=Decimal("0.01"),
        fixed_fee=Decimal("0.50"),
    )
    assert trade is not None
    assert trade.quantity == -40
    assert trade.fee == Decimal("0.90")
    assert session.ledger.snapshot(
        "market-maker", Decimal("2.50"), Decimal("105")
    ).stock_inventory == 80

    no_trade = session.ledger.rebalance_delta(
        "market-maker",
        option_delta=Decimal("0.40"),
        stock_price=Decimal("105"),
        per_share_fee=Decimal("0.01"),
        fixed_fee=Decimal("0.50"),
    )
    assert no_trade is None
