from math import exp

import pytest

from volforge import OptionType, black_scholes


def test_put_call_parity_and_delta_signs() -> None:
    inputs = dict(
        spot=100.0,
        strike=105.0,
        years_to_expiry=0.25,
        risk_free_rate=0.03,
        volatility=0.28,
    )
    call = black_scholes(OptionType.CALL, **inputs)
    put = black_scholes(OptionType.PUT, **inputs)
    parity = inputs["spot"] - inputs["strike"] * exp(
        -inputs["risk_free_rate"] * inputs["years_to_expiry"]
    )

    assert (call.price - put.price) == pytest.approx(parity, abs=1e-10)
    assert 0 < call.delta < 1
    assert -1 < put.delta < 0
    assert call.gamma == pytest.approx(put.gamma)
