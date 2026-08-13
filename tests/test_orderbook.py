from decimal import Decimal

from volforge import PriceTimeOrderBook, Side


def test_price_time_priority_uses_price_then_arrival() -> None:
    book = PriceTimeOrderBook("CALL-100")
    book.submit(order_id="ask-late-price", participant_id="maker-a", side=Side.SELL, price=Decimal("2.10"), quantity=2)
    book.submit(order_id="ask-first", participant_id="maker-b", side=Side.SELL, price=Decimal("2.00"), quantity=1)
    book.submit(order_id="ask-second", participant_id="maker-c", side=Side.SELL, price=Decimal("2.00"), quantity=1)

    fills = book.submit(order_id="buy", participant_id="taker", side=Side.BUY, price=Decimal("2.10"), quantity=3)

    assert [fill.maker_order_id for fill in fills] == ["ask-first", "ask-second", "ask-late-price"]
    assert [fill.price for fill in fills] == [Decimal("2.00"), Decimal("2.00"), Decimal("2.10")]
    assert sum(fill.quantity for fill in fills) == 3


def test_cancelled_order_cannot_trade() -> None:
    book = PriceTimeOrderBook("PUT-95")
    book.submit(order_id="ask", participant_id="maker", side=Side.SELL, price=Decimal("1.25"), quantity=2)
    book.cancel("ask")
    fills = book.submit(order_id="buy", participant_id="taker", side=Side.BUY, price=Decimal("1.25"), quantity=2)
    assert fills == ()

