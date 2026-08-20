from fastapi.testclient import TestClient

from volforge.api import create_app


def test_hedge_event_and_attribution_survive_restart(tmp_path) -> None:
    database = tmp_path / "volforge.db"
    client = TestClient(create_app(database))
    created = client.post("/v1/sessions", json={"symbol": "WIRTZ-C100"}).json()
    session_id = created["session_id"]
    for participant in ("market-maker", "directional-trader"):
        assert client.post(
            f"/v1/sessions/{session_id}/participants",
            json={"participant_id": participant, "starting_cash": "10000"},
        ).status_code == 200
    assert client.post(
        f"/v1/sessions/{session_id}/orders",
        json={
            "order_id": "maker-ask",
            "participant_id": "market-maker",
            "side": "sell",
            "price": "2.10",
            "quantity": 2,
        },
    ).status_code == 200
    assert client.post(
        f"/v1/sessions/{session_id}/orders",
        json={
            "order_id": "trader-buy",
            "participant_id": "directional-trader",
            "side": "buy",
            "price": "2.10",
            "quantity": 2,
        },
    ).status_code == 200

    hedged = client.post(
        f"/v1/sessions/{session_id}/hedges",
        json={
            "participant_id": "market-maker",
            "option_delta": "0.60",
            "stock_price": "100",
            "per_share_fee": "0.01",
            "fixed_fee": "0.50",
        },
    )
    assert hedged.status_code == 200
    assert hedged.json()["account"]["stock_inventory"] == 120
    assert hedged.json()["session"]["events"][-1]["event_type"] == "stock_hedge.executed"

    restarted = TestClient(create_app(database))
    account = restarted.get(
        f"/v1/sessions/{session_id}/accounts/market-maker",
        params={"option_mark": "2.50", "stock_mark": "105"},
    )
    assert account.status_code == 200
    assert account.json()["attribution"] == {
        "option_pnl": "-80.00",
        "hedge_pnl": "600",
        "fees": "1.70",
        "total_pnl": "518.30",
    }
    assert account.json()["pnl"] == "518.30"
