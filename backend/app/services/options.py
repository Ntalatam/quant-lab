"""
Options pricing and Greeks analytics.

Provides Black-Scholes pricing, full Greeks computation, implied volatility
via Newton-Raphson, and volatility surface generation for visualization.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

# ── Core pricing ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OptionResult:
    """Full result from Black-Scholes pricing."""

    price: float
    delta: float
    gamma: float
    theta: float  # per calendar day
    vega: float  # per 1% vol move
    rho: float  # per 1% rate move
    intrinsic: float
    time_value: float


def black_scholes(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
) -> OptionResult:
    """
    Black-Scholes-Merton pricing with full Greeks.

    Parameters
    ----------
    S : Spot price
    K : Strike price
    T : Time to expiry in years (e.g. 30/365 = 0.0822)
    r : Risk-free rate (annualized, e.g. 0.05 for 5%)
    sigma : Implied volatility (annualized, e.g. 0.20 for 20%)
    option_type : "call" or "put"
    """
    if T <= 0:
        # At or past expiry → intrinsic only
        if option_type == "call":
            intrinsic = max(S - K, 0)
        else:
            intrinsic = max(K - S, 0)
        return OptionResult(
            price=intrinsic,
            delta=1.0 if intrinsic > 0 else 0.0,
            gamma=0,
            theta=0,
            vega=0,
            rho=0,
            intrinsic=intrinsic,
            time_value=0,
        )

    if sigma <= 0:
        sigma = 1e-10

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    nd1 = norm.cdf(d1)
    nd2 = norm.cdf(d2)
    n_prime_d1 = norm.pdf(d1)

    if option_type == "call":
        price = S * nd1 - K * math.exp(-r * T) * nd2
        delta = nd1
        intrinsic = max(S - K, 0)
        rho = K * T * math.exp(-r * T) * nd2 / 100
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = nd1 - 1
        intrinsic = max(K - S, 0)
        rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100

    gamma = n_prime_d1 / (S * sigma * sqrt_T)
    theta = (
        -(S * n_prime_d1 * sigma) / (2 * sqrt_T)
        - r * K * math.exp(-r * T) * (nd2 if option_type == "call" else norm.cdf(-d2))
    ) / 365  # per calendar day
    vega = S * n_prime_d1 * sqrt_T / 100  # per 1% vol move

    return OptionResult(
        price=round(price, 4),
        delta=round(delta, 4),
        gamma=round(gamma, 6),
        theta=round(theta, 4),
        vega=round(vega, 4),
        rho=round(rho, 4),
        intrinsic=round(intrinsic, 4),
        time_value=round(price - intrinsic, 4),
    )


# ── Implied volatility ───────────────────────────────────────────────────


def implied_volatility(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = "call",
) -> float | None:
    """
    Solve for implied volatility using Brent's method.

    Returns None if the market price is below intrinsic or no solution found.
    """
    if T <= 0:
        return None

    intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
    if market_price < intrinsic - 0.001:
        return None

    def objective(sigma: float) -> float:
        return black_scholes(S, K, T, r, sigma, option_type).price - market_price

    try:
        iv = brentq(objective, 1e-6, 5.0, xtol=1e-6, maxiter=100)
        return round(iv, 6)
    except (ValueError, RuntimeError):
        return None


# ── Options chain (synthetic) ─────────────────────────────────────────────


def generate_options_chain(
    S: float,
    r: float,
    sigma: float,
    days_to_expiry: list[int],
    strike_range_pct: float = 0.20,
    n_strikes: int = 15,
) -> list[dict]:
    """
    Generate a synthetic options chain with calls and puts across
    multiple expiries and strikes.
    """
    strikes = np.linspace(S * (1 - strike_range_pct), S * (1 + strike_range_pct), n_strikes)
    strikes = np.round(strikes, 2)

    chain = []
    for dte in days_to_expiry:
        T = dte / 365.0
        for K_val in strikes:
            K = float(K_val)
            call = black_scholes(S, K, T, r, sigma, "call")
            put = black_scholes(S, K, T, r, sigma, "put")
            chain.append(
                {
                    "dte": dte,
                    "strike": K,
                    "call_price": call.price,
                    "call_delta": call.delta,
                    "call_gamma": call.gamma,
                    "call_theta": call.theta,
                    "call_vega": call.vega,
                    "put_price": put.price,
                    "put_delta": put.delta,
                    "put_gamma": put.gamma,
                    "put_theta": put.theta,
                    "put_vega": put.vega,
                    "moneyness": round(K / S, 4),
                }
            )
    return chain


# ── Volatility surface ───────────────────────────────────────────────────


def generate_vol_surface(
    S: float,
    r: float,
    base_sigma: float,
    days_to_expiry: list[int] | None = None,
    n_strikes: int = 21,
    strike_range_pct: float = 0.25,
) -> dict:
    """
    Generate a synthetic implied volatility surface with realistic skew.

    Models the volatility smile/skew as:
      IV(K) = base_sigma * (1 + skew_factor * (moneyness - 1)^2 + put_skew * min(moneyness - 1, 0))

    where:
      - skew_factor controls the curvature (smile)
      - put_skew adds extra vol to OTM puts (realistic for equities)
      - Term structure: short-dated options have steeper skew
    """
    if days_to_expiry is None:
        days_to_expiry = [7, 14, 30, 60, 90, 120, 180, 365]

    strikes = np.linspace(S * (1 - strike_range_pct), S * (1 + strike_range_pct), n_strikes)
    strikes = np.round(strikes, 2)
    moneyness = strikes / S

    surface: list[dict] = []
    for dte in days_to_expiry:
        T = dte / 365.0
        # Steeper skew for short-dated options
        smile_factor = 1.5 / (1 + T * 3)
        # Asymmetric skew: OTM puts get extra vol (equity skew)
        put_skew = 2.0 / (1 + T * 2)

        for i, K_val in enumerate(strikes):
            m = float(moneyness[i])
            # Quadratic smile + linear put skew (negative for OTM puts)
            iv = base_sigma * (1 + smile_factor * (m - 1) ** 2 - put_skew * min(m - 1, 0))
            iv = max(iv, 0.01)  # floor at 1%
            surface.append(
                {
                    "dte": dte,
                    "strike": float(K_val),
                    "moneyness": round(m, 4),
                    "implied_vol": round(iv, 4),
                }
            )

    return {
        "spot": S,
        "base_vol": base_sigma,
        "strikes": [float(k) for k in strikes],
        "expiries": days_to_expiry,
        "surface": surface,
    }


# ── P&L scenarios ────────────────────────────────────────────────────────


def compute_pnl_grid(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str,
    position: int,  # +1 long, -1 short
    entry_price: float | None = None,
    price_range_pct: float = 0.15,
    n_points: int = 50,
    dte_slices: list[int] | None = None,
) -> dict:
    """
    Compute option P&L across a grid of spot prices and time-to-expiry values.
    """
    if entry_price is None:
        entry_price = black_scholes(S, K, T, r, sigma, option_type).price

    if dte_slices is None:
        total_dte = int(T * 365)
        dte_slices = sorted(set([total_dte, max(total_dte // 2, 1), max(total_dte // 4, 1), 1, 0]))

    spot_range = np.linspace(S * (1 - price_range_pct), S * (1 + price_range_pct), n_points)

    curves: list[dict] = []
    for dte in dte_slices:
        t = max(dte / 365.0, 0)
        points = []
        for spot in spot_range:
            result = black_scholes(float(spot), K, t, r, sigma, option_type)
            pnl = (result.price - entry_price) * position * 100  # per contract
            points.append(
                {
                    "spot": round(float(spot), 2),
                    "pnl": round(pnl, 2),
                }
            )
        curves.append(
            {
                "dte": dte,
                "label": f"{dte}d" if dte > 0 else "Expiry",
                "points": points,
            }
        )

    return {
        "strike": K,
        "entry_price": round(entry_price, 4),
        "position": "long" if position > 0 else "short",
        "option_type": option_type,
        "curves": curves,
    }
