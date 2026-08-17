from fastapi.testclient import TestClient

from volforge.api import create_app


def test_earnings_analysis_is_stateless_and_explains_benchmarks(tmp_path) -> None:
    client = TestClient(create_app(tmp_path / "volforge.db"))

    response = client.post(
        "/v1/analysis/earnings",
        json={
            "outcomes": [
                {"label": "beat", "probability": "0.4", "stock_return": "0.12"},
                {"label": "inline", "probability": "0.3", "stock_return": "0.01"},
                {"label": "miss", "probability": "0.3", "stock_return": "-0.10"},
            ],
            "spot": "100",
            "strike": "100",
            "premium": "4",
            "chosen_action": "buy_call",
            "risk_preset": "balanced",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["storage"] == "stateless"
    assert len(payload["analyses"]) == 3
    assert payload["expected_value_benchmark"] in {
        "buy_call",
        "sell_call",
        "stay_flat",
    }


def test_session_commands_survive_app_restart(tmp_path) -> None:
    database = tmp_path / "volforge.db"
    first_client = TestClient(create_app(database))
    created = first_client.post(
        "/v1/sessions", json={"symbol": "wirtz", "tick_size": "0.05"}
    )
    assert created.status_code == 201
    session_id = created.json()["session_id"]

    registered = first_client.post(
        f"/v1/sessions/{session_id}/participants",
        json={"participant_id": "maker", "starting_cash": "10000.00"},
    )
    assert registered.status_code == 200
    submitted = first_client.post(
        f"/v1/sessions/{session_id}/orders",
        json={
            "order_id": "ask-1",
            "participant_id": "maker",
            "side": "sell",
            "price": "3.25",
            "quantity": 2,
        },
    )
    assert submitted.status_code == 200

    restarted_client = TestClient(create_app(database))
    replayed = restarted_client.get(f"/v1/sessions/{session_id}")
    assert replayed.status_code == 200
    payload = replayed.json()
    assert payload["symbol"] == "WIRTZ"
    assert [event["event_type"] for event in payload["events"]] == [
        "participant.registered",
        "order.accepted",
    ]
    assert payload["active_orders"][0]["remaining"] == 2
    assert payload["active_orders"][0]["price"] == "3.25"
