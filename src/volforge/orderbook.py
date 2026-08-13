from __future__ import annotations

from collections import defaultdict, deque
from decimal import Decimal

from .contracts import Fill, Order, Side


class PriceTimeOrderBook:
    """Single-instrument limit book with deterministic price-time priority."""

    def __init__(self, symbol: str, tick_size: Decimal = Decimal("0.01")) -> None:
        if tick_size <= 0:
            raise ValueError("tick_size must be positive")
        self.symbol = symbol
        self.tick_size = tick_size
        self._orders: dict[str, Order] = {}
        self._levels: dict[Side, dict[Decimal, deque[str]]] = {
            Side.BUY: defaultdict(deque),
            Side.SELL: defaultdict(deque),
        }
        self._sequence = 0
        self._fill_sequence = 0

    def submit(
        self,
        *,
        order_id: str,
        participant_id: str,
        side: Side,
        price: Decimal,
        quantity: int,
    ) -> tuple[Fill, ...]:
        if order_id in self._orders:
            raise ValueError("order_id already exists")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if price <= 0 or price % self.tick_size != 0:
            raise ValueError("price must be positive and aligned to tick_size")

        self._sequence += 1
        incoming = Order(
            order_id=order_id,
            participant_id=participant_id,
            side=side,
            price=price,
            quantity=quantity,
            remaining=quantity,
            sequence=self._sequence,
        )
        self._orders[order_id] = incoming
        fills: list[Fill] = []

        while incoming.remaining and (resting := self._best_crossing_order(incoming)):
            trade_quantity = min(incoming.remaining, resting.remaining)
            incoming.remaining -= trade_quantity
            resting.remaining -= trade_quantity
            self._fill_sequence += 1
            buyer = incoming if incoming.side is Side.BUY else resting
            seller = incoming if incoming.side is Side.SELL else resting
            fills.append(
                Fill(
                    fill_id=f"fill-{self._fill_sequence}",
                    maker_order_id=resting.order_id,
                    taker_order_id=incoming.order_id,
                    price=resting.price,
                    quantity=trade_quantity,
                    buy_participant_id=buyer.participant_id,
                    sell_participant_id=seller.participant_id,
                    sequence=self._fill_sequence,
                )
            )
            if resting.remaining == 0:
                self._remove_from_level(resting)

        if incoming.remaining:
            self._levels[incoming.side][incoming.price].append(incoming.order_id)
        return tuple(fills)

    def cancel(self, order_id: str) -> None:
        order = self._orders.get(order_id)
        if order is None or order.remaining == 0:
            raise ValueError("order is not active")
        self._remove_from_level(order)
        order.remaining = 0

    def active_order(self, order_id: str) -> Order | None:
        order = self._orders.get(order_id)
        return order if order is not None and order.remaining else None

    def _best_crossing_order(self, incoming: Order) -> Order | None:
        opposing = Side.SELL if incoming.side is Side.BUY else Side.BUY
        prices = [price for price, queue in self._levels[opposing].items() if queue]
        if not prices:
            return None
        best_price = min(prices) if opposing is Side.SELL else max(prices)
        crosses = incoming.price >= best_price if incoming.side is Side.BUY else incoming.price <= best_price
        if not crosses:
            return None
        return self._orders[self._levels[opposing][best_price][0]]

    def _remove_from_level(self, order: Order) -> None:
        queue = self._levels[order.side][order.price]
        try:
            queue.remove(order.order_id)
        except ValueError:
            return
        if not queue:
            del self._levels[order.side][order.price]

