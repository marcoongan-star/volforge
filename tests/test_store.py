from decimal import Decimal

import pytest

from volforge import Side, SqliteSessionStore


def test_session_events_survive_store_restart_and_replay(tmp_path) -> None:
    path = tmp_path / "volforge.db"
    store = SqliteSessionStore(path)
    store.create_session("earnings-1", "WIRTZ-C100")
    session = store.mutate(
        "earnings-1",
        lambda active: active.register_participant("maker", Decimal("10000")),
    )
    store.mutate(
        "earnings-1",
        lambda active: active.submit_order(
            order_id="ask-1",
            participant_id="maker",
            side=Side.SELL,
            price=Decimal("2.10"),
            quantity=3,
        ),
    )

    restarted = SqliteSessionStore(path)
    replay = restarted.load("earnings-1")

    assert replay.log.events[-1].data()["order_id"] == "ask-1"
    assert replay.active_orders()[0].remaining == 3
    assert replay.log.events[0] == session.log.events[0]


def test_store_rejects_duplicate_session_ids_and_event_rewrites(tmp_path) -> None:
    store = SqliteSessionStore(tmp_path / "volforge.db")
    session = store.create_session("earnings-1", "WIRTZ-C100")
    session.register_participant("maker", Decimal("10000"))
    store.append_new_events("earnings-1", session.log.events)

    with pytest.raises(ValueError, match="already exists"):
        store.create_session("earnings-1", "OTHER")
    with pytest.raises(ValueError, match="sequence 2"):
        store.append_new_events("earnings-1", session.log.events)
