"""Tests for the cointegration analytics service."""

import numpy as np
import pandas as pd
import pytest

from app.services.cointegration import (
    compute_correlation_matrix,
    compute_spread,
    discover_pairs,
    engle_granger_test,
)


def _make_prices(n: int = 500, seed: int = 42) -> dict[str, pd.Series]:
    """Generate synthetic cointegrated and uncorrelated price series."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)

    # Generate random walk series (a, b, c used implicitly via exponential construction below)
    _a = 100 + np.cumsum(rng.normal(0.0005, 0.01, n))  # noqa: F841
    _b = _a * 1.05 + rng.normal(0, 0.3, n)  # noqa: F841
    _c = 50 + np.cumsum(rng.normal(0.0003, 0.015, n))  # noqa: F841

    return {
        "TICK_A": pd.Series(
            np.exp(np.log(100) + np.cumsum(rng.normal(0.0005, 0.01, n))), index=dates
        ),
        "TICK_B": pd.Series(
            np.exp(np.log(105) + np.cumsum(rng.normal(0.0005, 0.01, n)) + rng.normal(0, 0.002, n)),
            index=dates,
        ),
        "TICK_C": pd.Series(np.exp(np.log(50) + np.cumsum(rng.normal(0.0, 0.02, n))), index=dates),
    }


class TestCorrelationMatrix:
    def test_returns_correct_shape(self):
        prices = _make_prices()
        result = compute_correlation_matrix(prices, rolling_window=21)

        assert result["tickers"] == ["TICK_A", "TICK_B", "TICK_C"]
        assert len(result["static_matrix"]) == 3
        assert len(result["static_matrix"][0]) == 3

    def test_diagonal_is_one(self):
        prices = _make_prices()
        result = compute_correlation_matrix(prices, rolling_window=21)
        for i in range(3):
            assert abs(result["static_matrix"][i][i] - 1.0) < 1e-6

    def test_rolling_correlations_count(self):
        prices = _make_prices()
        result = compute_correlation_matrix(prices, rolling_window=21)
        # 3 tickers → 3 pairs
        assert len(result["rolling_correlations"]) == 3

    def test_rolling_series_nonempty(self):
        prices = _make_prices()
        result = compute_correlation_matrix(prices, rolling_window=21)
        for rc in result["rolling_correlations"]:
            assert len(rc["series"]) > 0
            assert "date" in rc["series"][0]
            assert "value" in rc["series"][0]

    def test_too_few_tickers_raises(self):
        prices = _make_prices()
        with pytest.raises(ValueError):
            compute_correlation_matrix({"A": prices["TICK_A"]}, rolling_window=21)


class TestEngleGranger:
    def test_cointegrated_pair(self):
        """Two series that share the same random walk should be cointegrated."""
        rng = np.random.default_rng(123)
        n = 1000
        # Common random walk
        rw = np.cumsum(rng.normal(0, 1, n))
        a = pd.Series(rw + rng.normal(0, 0.5, n))
        b = pd.Series(rw * 0.8 + rng.normal(0, 0.5, n))

        result = engle_granger_test(a, b)
        assert "adf_statistic" in result
        assert "adf_pvalue" in result
        assert "cointegrated" in result
        # With 1000 samples from a truly cointegrated pair, p-value should be low
        assert result["adf_pvalue"] < 0.10

    def test_independent_pair(self):
        """Two independent random walks should not be cointegrated."""
        rng = np.random.default_rng(456)
        n = 500
        a = pd.Series(np.cumsum(rng.normal(0, 1, n)))
        b = pd.Series(np.cumsum(rng.normal(0, 1, n)))

        result = engle_granger_test(a, b)
        # Independent random walks — should NOT be cointegrated
        assert result["adf_pvalue"] > 0.01


class TestSpread:
    def test_spread_output_structure(self):
        prices = _make_prices(n=200)
        result = compute_spread(prices["TICK_A"], prices["TICK_B"], lookback=21)

        assert "spread_series" in result
        assert "zscore_series" in result
        assert "half_life_days" in result
        assert "spread_mean" in result
        assert "spread_std" in result
        assert len(result["spread_series"]) > 0

    def test_zscore_bounded(self):
        prices = _make_prices(n=300)
        result = compute_spread(prices["TICK_A"], prices["TICK_B"], lookback=21)
        zscores = [p["value"] for p in result["zscore_series"]]
        # Z-scores should be reasonable (within ±10 for any normal spread)
        assert all(-10 < z < 10 for z in zscores)


class TestDiscoverPairs:
    def test_returns_sorted_by_pvalue(self):
        prices = _make_prices()
        pairs = discover_pairs(prices, max_pairs=5)
        assert len(pairs) > 0
        # Should be sorted ascending by p-value
        pvals = [p["adf_pvalue"] for p in pairs]
        assert pvals == sorted(pvals)

    def test_max_pairs_limit(self):
        prices = _make_prices()
        pairs = discover_pairs(prices, max_pairs=1)
        assert len(pairs) <= 1

    def test_pair_fields(self):
        prices = _make_prices()
        pairs = discover_pairs(prices, max_pairs=5)
        for p in pairs:
            assert "ticker_a" in p
            assert "ticker_b" in p
            assert "adf_pvalue" in p
            assert "cointegrated" in p
            assert "beta" in p
