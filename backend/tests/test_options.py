"""Tests for Black-Scholes pricing, Greeks, IV solver, and vol surface."""

import math

from app.services.options import (
    black_scholes,
    compute_pnl_grid,
    generate_options_chain,
    generate_vol_surface,
    implied_volatility,
)


class TestBlackScholes:
    """Core pricing and Greeks tests."""

    def test_call_price_positive(self):
        r = black_scholes(100, 100, 0.25, 0.05, 0.20, "call")
        assert r.price > 0

    def test_put_price_positive(self):
        r = black_scholes(100, 100, 0.25, 0.05, 0.20, "put")
        assert r.price > 0

    def test_put_call_parity(self):
        """C - P = S - K*exp(-rT)."""
        S, K, T, r, sigma = 100, 105, 0.5, 0.05, 0.25
        call = black_scholes(S, K, T, r, sigma, "call")
        put = black_scholes(S, K, T, r, sigma, "put")
        parity = S - K * math.exp(-r * T)
        assert abs((call.price - put.price) - parity) < 0.01

    def test_call_delta_range(self):
        r = black_scholes(100, 100, 0.25, 0.05, 0.20, "call")
        assert 0 <= r.delta <= 1

    def test_put_delta_range(self):
        r = black_scholes(100, 100, 0.25, 0.05, 0.20, "put")
        assert -1 <= r.delta <= 0

    def test_gamma_positive(self):
        r = black_scholes(100, 100, 0.25, 0.05, 0.20, "call")
        assert r.gamma > 0

    def test_call_gamma_equals_put_gamma(self):
        call = black_scholes(100, 100, 0.25, 0.05, 0.20, "call")
        put = black_scholes(100, 100, 0.25, 0.05, 0.20, "put")
        assert abs(call.gamma - put.gamma) < 1e-6

    def test_vega_positive(self):
        r = black_scholes(100, 100, 0.25, 0.05, 0.20, "call")
        assert r.vega > 0

    def test_theta_negative_for_long(self):
        """Long options lose value over time (theta < 0)."""
        r = black_scholes(100, 100, 0.25, 0.05, 0.20, "call")
        assert r.theta < 0

    def test_deep_itm_call_delta_near_one(self):
        r = black_scholes(200, 100, 1.0, 0.05, 0.20, "call")
        assert r.delta > 0.95

    def test_deep_otm_call_delta_near_zero(self):
        r = black_scholes(50, 100, 0.1, 0.05, 0.20, "call")
        assert r.delta < 0.05

    def test_expired_option(self):
        """At expiry, value = intrinsic."""
        r = black_scholes(110, 100, 0, 0.05, 0.20, "call")
        assert r.price == 10
        assert r.delta == 1.0
        assert r.gamma == 0

    def test_intrinsic_and_time_value(self):
        r = black_scholes(110, 100, 0.25, 0.05, 0.20, "call")
        assert r.intrinsic == 10
        assert r.time_value > 0
        assert abs(r.price - r.intrinsic - r.time_value) < 0.01


class TestImpliedVolatility:
    def test_round_trip(self):
        """Price → IV → re-price should match."""
        original_vol = 0.25
        S, K, T, r = 100, 105, 0.5, 0.05
        price = black_scholes(S, K, T, r, original_vol, "call").price
        iv = implied_volatility(price, S, K, T, r, "call")
        assert iv is not None
        assert abs(iv - original_vol) < 0.001

    def test_put_round_trip(self):
        original_vol = 0.30
        S, K, T, r = 100, 95, 0.25, 0.04
        price = black_scholes(S, K, T, r, original_vol, "put").price
        iv = implied_volatility(price, S, K, T, r, "put")
        assert iv is not None
        assert abs(iv - original_vol) < 0.001

    def test_below_intrinsic_returns_none(self):
        """Price below intrinsic → no valid IV."""
        iv = implied_volatility(0.01, 100, 50, 0.5, 0.05, "call")
        assert iv is None


class TestOptionsChain:
    def test_chain_structure(self):
        chain = generate_options_chain(150, 0.05, 0.25, [30, 60], n_strikes=5)
        assert len(chain) == 2 * 5  # 2 expiries × 5 strikes
        entry = chain[0]
        assert "call_price" in entry
        assert "put_price" in entry
        assert "call_delta" in entry
        assert "moneyness" in entry

    def test_chain_moneyness(self):
        chain = generate_options_chain(100, 0.05, 0.20, [30], n_strikes=11)
        # Middle strike should be near ATM (moneyness ≈ 1.0)
        middle = chain[5]
        assert abs(middle["moneyness"] - 1.0) < 0.05


class TestVolSurface:
    def test_surface_structure(self):
        result = generate_vol_surface(150, 0.05, 0.25, n_strikes=5)
        assert "strikes" in result
        assert "expiries" in result
        assert "surface" in result
        assert len(result["strikes"]) == 5
        assert len(result["expiries"]) == 8  # default expiries

    def test_put_skew(self):
        """Deep OTM puts should have higher IV than OTM calls at same distance from ATM."""
        result = generate_vol_surface(100, 0.05, 0.25, [30], n_strikes=21)
        surface = result["surface"]
        # Compare IV at symmetric distance: 0.85 moneyness vs 1.15 moneyness
        otm_put = min(surface, key=lambda p: abs(p["moneyness"] - 0.80))
        otm_call = min(surface, key=lambda p: abs(p["moneyness"] - 1.20))
        assert otm_put["implied_vol"] > otm_call["implied_vol"]

    def test_term_structure_skew_flattening(self):
        """Longer-dated options should have less steep skew."""
        result = generate_vol_surface(100, 0.05, 0.25, [7, 365], n_strikes=11)
        short_dated = [p for p in result["surface"] if p["dte"] == 7]
        long_dated = [p for p in result["surface"] if p["dte"] == 365]

        # Compare the IV range (max - min) for each term
        short_range = max(p["implied_vol"] for p in short_dated) - min(
            p["implied_vol"] for p in short_dated
        )
        long_range = max(p["implied_vol"] for p in long_dated) - min(
            p["implied_vol"] for p in long_dated
        )
        assert short_range > long_range


class TestPnlGrid:
    def test_pnl_structure(self):
        result = compute_pnl_grid(100, 105, 30 / 365, 0.05, 0.25, "call", 1)
        assert "curves" in result
        assert len(result["curves"]) > 0
        assert result["position"] == "long"
        for curve in result["curves"]:
            assert len(curve["points"]) > 0

    def test_long_call_max_loss(self):
        """Long call max loss = entry premium × 100."""
        result = compute_pnl_grid(100, 100, 30 / 365, 0.05, 0.25, "call", 1)
        expiry_curve = next(c for c in result["curves"] if c["dte"] == 0)
        min_pnl = min(p["pnl"] for p in expiry_curve["points"])
        assert abs(min_pnl + result["entry_price"] * 100) < 1.0

    def test_short_put_pnl_inverted(self):
        """Short option P&L is the mirror of long."""
        long_r = compute_pnl_grid(100, 100, 30 / 365, 0.05, 0.25, "put", 1)
        short_r = compute_pnl_grid(100, 100, 30 / 365, 0.05, 0.25, "put", -1)
        # At same spot, PnLs should be opposite in sign
        l_pts = long_r["curves"][0]["points"]
        s_pts = short_r["curves"][0]["points"]
        for lp, sp in zip(l_pts, s_pts):
            assert abs(lp["pnl"] + sp["pnl"]) < 0.1
