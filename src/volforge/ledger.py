from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .contracts import Fill


@dataclass
class _Account:
    starting_cash: Decimal
    cash: Decimal
    option_inventory: int = 0
    option_trade_cash: Decimal = Decimal("0")
    stock_inventory: int = 0
    stock_trade_cash: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")


@dataclass(frozen=True)
class StockTrade:
    participant_id: str
    quantity: int
    price: Decimal
    fee: Decimal


@dataclass(frozen=True)
class PnlAttribution:
    option_pnl: Decimal
    hedge_pnl: Decimal
    fees: Decimal
    total_pnl: Decimal


@dataclass(frozen=True)
class AccountSnapshot:
    participant_id: str
    starting_cash: Decimal
    cash: Decimal
    option_inventory: int
    option_mark: Decimal
    inventory_value: Decimal
    stock_inventory: int
    stock_mark: Decimal
    stock_inventory_value: Decimal
    attribution: PnlAttribution
    equity: Decimal
    pnl: Decimal


class TradingLedger:
    """Double-entry-style cash and option inventory accounting for exchange fills."""

    def __init__(self, contract_multiplier: int = 100) -> None:
        if contract_multiplier <= 0:
            raise ValueError("contract_multiplier must be positive")
        self.contract_multiplier = contract_multiplier
        self._accounts: dict[str, _Account] = {}

    def register(self, participant_id: str, starting_cash: Decimal = Decimal("0")) -> None:
        if not participant_id.strip():
            raise ValueError("participant_id is required")
        if participant_id in self._accounts:
            raise ValueError("participant is already registered")
        self._accounts[participant_id] = _Account(starting_cash, starting_cash)

    def apply_fill(self, fill: Fill) -> None:
        buyer = self._account(fill.buy_participant_id)
        seller = self._account(fill.sell_participant_id)
        premium = fill.price * fill.quantity * self.contract_multiplier

        buyer.cash -= premium
        buyer.option_inventory += fill.quantity
        buyer.option_trade_cash -= premium
        seller.cash += premium
        seller.option_inventory -= fill.quantity
        seller.option_trade_cash += premium

    def rebalance_delta(
        self,
        participant_id: str,
        *,
        option_delta: Decimal,
        stock_price: Decimal,
        per_share_fee: Decimal = Decimal("0"),
        fixed_fee: Decimal = Decimal("0"),
    ) -> StockTrade | None:
        if not Decimal("-1") <= option_delta <= Decimal("1"):
            raise ValueError("option_delta must be between negative one and one")
        if stock_price <= 0:
            raise ValueError("stock_price must be positive")
        if per_share_fee < 0 or fixed_fee < 0:
            raise ValueError("fees cannot be negative")
        account = self._account(participant_id)
        target = int(
            (
                -Decimal(account.option_inventory)
                * option_delta
                * Decimal(self.contract_multiplier)
            ).to_integral_value(rounding=ROUND_HALF_UP)
        )
        quantity = target - account.stock_inventory
        if quantity == 0:
            return None
        fee = abs(quantity) * per_share_fee + fixed_fee
        account.cash -= Decimal(quantity) * stock_price + fee
        account.stock_trade_cash -= Decimal(quantity) * stock_price
        account.stock_inventory += quantity
        account.fees += fee
        return StockTrade(participant_id, quantity, stock_price, fee)

    def apply_stock_trade(self, trade: StockTrade) -> None:
        if trade.quantity == 0 or trade.price <= 0 or trade.fee < 0:
            raise ValueError("stock trade must have quantity, positive price, and nonnegative fee")
        account = self._account(trade.participant_id)
        account.cash -= Decimal(trade.quantity) * trade.price + trade.fee
        account.stock_trade_cash -= Decimal(trade.quantity) * trade.price
        account.stock_inventory += trade.quantity
        account.fees += trade.fee

    def snapshot(
        self,
        participant_id: str,
        option_mark: Decimal,
        stock_mark: Decimal = Decimal("0"),
    ) -> AccountSnapshot:
        if option_mark < 0 or stock_mark < 0:
            raise ValueError("option_mark and stock_mark cannot be negative")
        account = self._account(participant_id)
        inventory_value = option_mark * account.option_inventory * self.contract_multiplier
        stock_inventory_value = stock_mark * account.stock_inventory
        option_pnl = account.option_trade_cash + inventory_value
        hedge_pnl = account.stock_trade_cash + stock_inventory_value
        attribution = PnlAttribution(
            option_pnl=option_pnl,
            hedge_pnl=hedge_pnl,
            fees=account.fees,
            total_pnl=option_pnl + hedge_pnl - account.fees,
        )
        equity = account.cash + inventory_value + stock_inventory_value
        return AccountSnapshot(
            participant_id=participant_id,
            starting_cash=account.starting_cash,
            cash=account.cash,
            option_inventory=account.option_inventory,
            option_mark=option_mark,
            inventory_value=inventory_value,
            stock_inventory=account.stock_inventory,
            stock_mark=stock_mark,
            stock_inventory_value=stock_inventory_value,
            attribution=attribution,
            equity=equity,
            pnl=equity - account.starting_cash,
        )

    def _account(self, participant_id: str) -> _Account:
        account = self._accounts.get(participant_id)
        if account is None:
            account = _Account(Decimal("0"), Decimal("0"))
            self._accounts[participant_id] = account
        return account
