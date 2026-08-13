from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, pi, sqrt

from .contracts import OptionType


@dataclass(frozen=True)
class OptionMetrics:
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def _normal_pdf(value: float) -> float:
    return exp(-0.5 * value * value) / sqrt(2.0 * pi)


def black_scholes(
    option_type: OptionType,
    spot: float,
    strike: float,
    years_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
) -> OptionMetrics:
    """Return European option metrics with theta expressed per calendar day."""

    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if years_to_expiry <= 0:
        raise ValueError("years_to_expiry must be positive")
    if volatility <= 0:
        raise ValueError("volatility must be positive")

    root_time = sqrt(years_to_expiry)
    d1 = (
        log(spot / strike)
        + (risk_free_rate + 0.5 * volatility * volatility) * years_to_expiry
    ) / (volatility * root_time)
    d2 = d1 - volatility * root_time
    discount = exp(-risk_free_rate * years_to_expiry)
    density = _normal_pdf(d1)

    gamma = density / (spot * volatility * root_time)
    vega = spot * density * root_time / 100.0
    common_theta = -(spot * density * volatility) / (2.0 * root_time)

    if option_type is OptionType.CALL:
        price = spot * _normal_cdf(d1) - strike * discount * _normal_cdf(d2)
        delta = _normal_cdf(d1)
        annual_theta = common_theta - risk_free_rate * strike * discount * _normal_cdf(d2)
    else:
        price = strike * discount * _normal_cdf(-d2) - spot * _normal_cdf(-d1)
        delta = _normal_cdf(d1) - 1.0
        annual_theta = common_theta + risk_free_rate * strike * discount * _normal_cdf(-d2)

    return OptionMetrics(
        price=price,
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=annual_theta / 365.0,
    )

