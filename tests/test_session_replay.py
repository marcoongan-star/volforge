from decimal import Decimal

import pytest

from volforge import EventType, SessionEvent, Side, TradingSession


def test_session_log_replays_to_identical_events_and_book_state() -> None:
    session = TradingSession("WIRTZ-C100")
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

    replay = TradingSession.replay(symbol=session.symbol, events=session.log.events)

    assert replay.log.events == session.log.events
    assert replay.active_orders() == session.active_orders()
    assert [event.event_type for event in session.log.events] == [
        EventType.ORDER_ACCEPTED,
        EventType.ORDER_ACCEPTED,
        EventType.FILL_CREATED,
    ]


def test_cancel_is_recorded_and_replayed() -> None:
    session = TradingSession("WIRTZ-P95")
    session.submit_order(
        order_id="bid-1",
        participant_id="market-maker",
        side=Side.BUY,
        price=Decimal("1.25"),
        quantity=2,
    )
    session.cancel_order("bid-1")

    replay = TradingSession.replay(symbol=session.symbol, events=session.log.events)
    assert replay.active_orders() == ()
    assert replay.log.events[-1].event_type is EventType.ORDER_CANCELLED


def test_replay_rejects_a_gap_in_event_sequence() -> None:
    broken = (
        SessionEvent(
            sequence=2,
            event_type=EventType.ORDER_CANCELLED,
            payload=(("order_id", "missing"),),
        ),
    )
    with pytest.raises(ValueError, match="contiguous"):
        TradingSession.replay(symbol="WIRTZ-C100", events=broken)
