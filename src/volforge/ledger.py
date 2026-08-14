from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .contracts import Fill


@dataclass
class _Account:
    starting_cash: Decimal
    cash: Decimal
    option_inventory: int = 0


@dataclass(frozen=True)
class AccountSnapshot:
    participant_id: str
    starting_cash: Decimal
    cash: Decimal
    option_inventory: int
    option_mark: Decimal
    inventory_value: Decimal
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
        seller.cash += premium
        seller.option_inventory -= fill.quantity

    def snapshot(self, participant_id: str, option_mark: Decimal) -> AccountSnapshot:
        if option_mark < 0:
            raise ValueError("option_mark cannot be negative")
        account = self._account(participant_id)
        inventory_value = option_mark * account.option_inventory * self.contract_multiplier
        equity = account.cash + inventory_value
        return AccountSnapshot(
            participant_id=participant_id,
            starting_cash=account.starting_cash,
            cash=account.cash,
            option_inventory=account.option_inventory,
            option_mark=option_mark,
            inventory_value=inventory_value,
            equity=equity,
            pnl=equity - account.starting_cash,
        )

    def _account(self, participant_id: str) -> _Account:
        account = self._accounts.get(participant_id)
        if account is None:
            account = _Account(Decimal("0"), Decimal("0"))
            self._accounts[participant_id] = account
        return account
