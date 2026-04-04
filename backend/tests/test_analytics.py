"""Tests for the analytics engine."""

import numpy as np
import pandas as pd

from app.services.analytics import (
    compute_all_metrics,
    compute_monte_carlo,
    compute_monthly_returns,
)


def _make_equity(values: list[float], start: str = "2023-01-02") -> pd.Series:
    idx = pd.bdate_range(start, periods=len(values))
    return pd.Series(values, index=idx)


class TestComputeAllMetrics:
    def test_flat_equity_has_zero_return(self):
        eq = _make_equity([100_000] * 252)
        bench = eq.copy()
        m = compute_all_metrics(eq, bench, 100_000)
        assert m["total_return_pct"] == 0

    def test_positive_return_detected(self):
        values = [100_000 + i * 100 for i in range(252)]
        eq = _make_equity(values)
        bench = eq.copy()
        m = compute_all_metrics(eq, bench, 100_000)
        assert m["total_return_pct"] > 0
        assert m["cagr_pct"] > 0

    def test_sharpe_ratio_positive_for_upward_equity(self):
        np.random.seed(42)
        daily_returns = np.random.normal(0.001, 0.01, 252)
        values = [100_000]
        for r in daily_returns:
            values.append(values[-1] * (1 + r))
        eq = _make_equity(values)
        bench = eq.copy()
        m = compute_all_metrics(eq, bench, 100_000)
        assert m["sharpe_ratio"] > 0

    def test_max_drawdown_negative(self):
        values = list(range(100_000, 110_000, 100)) + list(range(110_000, 100_000, -100))
        eq = _make_equity(values)
        bench = eq.copy()
        m = compute_all_metrics(eq, bench, 100_000)
        assert m["max_drawdown_pct"] < 0

    def test_var_95_negative(self):
        np.random.seed(42)
        daily_returns = np.random.normal(-0.001, 0.02, 252)
        values = [100_000]
        for r in daily_returns:
            values.append(values[-1] * (1 + r))
        eq = _make_equity(values)
        bench = eq.copy()
        m = compute_all_metrics(eq, bench, 100_000)
        assert m["var_95_pct"] < 0

    def test_empty_series_returns_zeros(self):
        eq = pd.Series(dtype=float)
        bench = pd.Series(dtype=float)
        m = compute_all_metrics(eq, bench, 100_000)
        assert m["total_return_pct"] == 0

    def test_short_series_returns_zeros(self):
        eq = pd.Series([100_000], index=pd.DatetimeIndex(["2023-01-02"]))
        bench = eq.copy()
        m = compute_all_metrics(eq, bench, 100_000)
        assert m["total_return_pct"] == 0


class TestComputeMonthlyReturns:
    def test_monthly_returns_structure(self):
        values = [100_000 + i * 10 for i in range(252)]
        eq = _make_equity(values)
        monthly = compute_monthly_returns(eq)
        assert len(monthly) > 0
        assert all("year" in m and "month" in m and "return_pct" in m for m in monthly)


class TestMonteCarlo:
    def test_monte_carlo_shape(self):
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        result = compute_monte_carlo(returns, n_simulations=100, n_days=50)
        assert "percentiles" in result
        assert len(result["percentiles"]["p50"]) == 50
        assert result["n_simulations"] == 100
        assert 0 <= result["prob_loss"] <= 1
