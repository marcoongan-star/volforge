from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .session import EventType, SessionEvent, TradingSession


@dataclass(frozen=True)
class StoredSession:
    session_id: str
    symbol: str
    tick_size: Decimal
    contract_multiplier: int


class SqliteSessionStore:
    """Append-only durable adapter for replayable trading sessions."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS trading_sessions (
                    session_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    tick_size TEXT NOT NULL,
                    contract_multiplier INTEGER NOT NULL CHECK (contract_multiplier > 0)
                );
                CREATE TABLE IF NOT EXISTS session_events (
                    session_id TEXT NOT NULL REFERENCES trading_sessions(session_id),
                    sequence INTEGER NOT NULL CHECK (sequence > 0),
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (session_id, sequence)
                );
                """
            )

    def create_session(
        self,
        session_id: str,
        symbol: str,
        *,
        tick_size: Decimal = Decimal("0.01"),
        contract_multiplier: int = 100,
    ) -> TradingSession:
        if not session_id.strip() or not symbol.strip():
            raise ValueError("session_id and symbol are required")
        session = TradingSession(symbol, tick_size, contract_multiplier)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO trading_sessions VALUES (?, ?, ?, ?)",
                    (session_id, symbol, str(tick_size), contract_multiplier),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("session_id already exists") from error
        return session

    def metadata(self, session_id: str) -> StoredSession:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM trading_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if row is None:
            raise KeyError(session_id)
        return StoredSession(
            session_id=row["session_id"],
            symbol=row["symbol"],
            tick_size=Decimal(row["tick_size"]),
            contract_multiplier=row["contract_multiplier"],
        )

    def append_new_events(
        self, session_id: str, events: tuple[SessionEvent, ...]
    ) -> None:
        if not events:
            return
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS last_sequence "
                "FROM session_events WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            expected = int(row["last_sequence"]) + 1
            if events[0].sequence != expected:
                raise ValueError(f"next persisted event must have sequence {expected}")
            for event in events:
                if event.sequence != expected:
                    raise ValueError("events must be contiguous")
                connection.execute(
                    "INSERT INTO session_events VALUES (?, ?, ?, ?)",
                    (
                        session_id,
                        event.sequence,
                        event.event_type.value,
                        json.dumps(event.data(), sort_keys=True, separators=(",", ":")),
                    ),
                )
                expected += 1

    def load(self, session_id: str) -> TradingSession:
        metadata = self.metadata(session_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT sequence, event_type, payload_json FROM session_events "
                "WHERE session_id = ? ORDER BY sequence",
                (session_id,),
            ).fetchall()
        events = tuple(
            SessionEvent(
                sequence=row["sequence"],
                event_type=EventType(row["event_type"]),
                payload=tuple(sorted(json.loads(row["payload_json"]).items())),
            )
            for row in rows
        )
        return TradingSession.replay(
            symbol=metadata.symbol,
            events=events,
            tick_size=metadata.tick_size,
            contract_multiplier=metadata.contract_multiplier,
        )

    def mutate(self, session_id: str, command) -> TradingSession:  # type: ignore[no-untyped-def]
        session = self.load(session_id)
        previous_count = len(session.log.events)
        command(session)
        self.append_new_events(session_id, session.log.events[previous_count:])
        return session
