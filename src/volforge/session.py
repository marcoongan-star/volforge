from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .contracts import Fill, Order, Side
from .orderbook import PriceTimeOrderBook


class EventType(StrEnum):
    ORDER_ACCEPTED = "order.accepted"
    ORDER_CANCELLED = "order.cancelled"
    FILL_CREATED = "fill.created"


@dataclass(frozen=True)
class SessionEvent:
    sequence: int
    event_type: EventType
    payload: tuple[tuple[str, str], ...]

    def data(self) -> dict[str, str]:
        return dict(self.payload)


class EventLog:
    """Append-only in-memory log; PostgreSQL persistence arrives with the API milestone."""

    def __init__(self) -> None:
        self._events: list[SessionEvent] = []

    @property
    def events(self) -> tuple[SessionEvent, ...]:
        return tuple(self._events)

    def append(self, event_type: EventType, **payload: object) -> SessionEvent:
        event = SessionEvent(
            sequence=len(self._events) + 1,
            event_type=event_type,
            payload=tuple(sorted((key, str(value)) for key, value in payload.items())),
        )
        self._events.append(event)
        return event


class TradingSession:
    """Command boundary that records every accepted exchange state change."""

    def __init__(self, symbol: str, tick_size: Decimal = Decimal("0.01")) -> None:
        self.symbol = symbol
        self.tick_size = tick_size
        self.book = PriceTimeOrderBook(symbol, tick_size)
        self.log = EventLog()

    def submit_order(
        self,
        *,
        order_id: str,
        participant_id: str,
        side: Side,
        price: Decimal,
        quantity: int,
    ) -> tuple[Fill, ...]:
        fills = self.book.submit(
            order_id=order_id,
            participant_id=participant_id,
            side=side,
            price=price,
            quantity=quantity,
        )
        self.log.append(
            EventType.ORDER_ACCEPTED,
            order_id=order_id,
            participant_id=participant_id,
            side=side.value,
            price=price,
            quantity=quantity,
        )
        for fill in fills:
            self.log.append(
                EventType.FILL_CREATED,
                fill_id=fill.fill_id,
                maker_order_id=fill.maker_order_id,
                taker_order_id=fill.taker_order_id,
                price=fill.price,
                quantity=fill.quantity,
                buy_participant_id=fill.buy_participant_id,
                sell_participant_id=fill.sell_participant_id,
            )
        return fills

    def cancel_order(self, order_id: str) -> None:
        self.book.cancel(order_id)
        self.log.append(EventType.ORDER_CANCELLED, order_id=order_id)

    def active_orders(self) -> tuple[Order, ...]:
        return self.book.active_orders()

    @classmethod
    def replay(
        cls,
        *,
        symbol: str,
        events: tuple[SessionEvent, ...],
        tick_size: Decimal = Decimal("0.01"),
    ) -> TradingSession:
        session = cls(symbol, tick_size)
        expected_sequence = 1
        for event in events:
            if event.sequence != expected_sequence:
                raise ValueError("event sequence must be contiguous")
            expected_sequence += 1
            data = event.data()
            if event.event_type is EventType.ORDER_ACCEPTED:
                session.submit_order(
                    order_id=data["order_id"],
                    participant_id=data["participant_id"],
                    side=Side(data["side"]),
                    price=Decimal(data["price"]),
                    quantity=int(data["quantity"]),
                )
            elif event.event_type is EventType.ORDER_CANCELLED:
                session.cancel_order(data["order_id"])
            elif event.event_type is not EventType.FILL_CREATED:
                raise ValueError(f"unsupported event type: {event.event_type}")
        if session.log.events != events:
            raise ValueError("replayed events do not match the source log")
        return session
