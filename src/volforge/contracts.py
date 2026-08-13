from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


@dataclass(frozen=True)
class OptionContract:
    symbol: str
    strike: Decimal
    expiry: date
    option_type: OptionType
    multiplier: int = 100


@dataclass
class Order:
    order_id: str
    participant_id: str
    side: Side
    price: Decimal
    quantity: int
    remaining: int
    sequence: int


@dataclass(frozen=True)
class Fill:
    fill_id: str
    maker_order_id: str
    taker_order_id: str
    price: Decimal
    quantity: int
    buy_participant_id: str
    sell_participant_id: str
    sequence: int

