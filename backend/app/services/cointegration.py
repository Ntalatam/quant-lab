"""
Correlation and cointegration analytics.

Provides rolling/static correlation matrices, Engle-Granger cointegration
tests, spread analysis with z-scores, half-life estimation, and automatic
tradeable pair discovery.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats


def compute_correlation_matrix(
    prices: dict[str, pd.Series],
    rolling_window: int = 63,
) -> dict:
    """
    Compute both a static full-period correlation matrix and rolling
    pairwise correlations for all supplied tickers.

    Parameters
    ----------
    prices : dict mapping ticker → pd.Series of daily close prices (DatetimeIndex)
    rolling_window : lookback in trading days for rolling correlation

    Returns
    -------
    dict with keys: tickers, static_matrix, rolling_correlations
    """
    df = pd.DataFrame(prices).sort_index().dropna()
    if df.shape[1] < 2 or len(df) < rolling_window:
        raise ValueError(
            f"Need at least 2 tickers with ≥{rolling_window} overlapping days"
        )

    returns = df.pct_change().dropna()
    tickers = list(df.columns)

    # Static correlation
    static = returns.corr().values.tolist()

    # Rolling pairwise correlations
    rolling: list[dict] = []
    pairs = list(combinations(range(len(tickers)), 2))
    for i, j in pairs:
        rc = returns.iloc[:, i].rolling(rolling_window).corr(returns.iloc[:, j]).dropna()
        rolling.append({
            "pair": f"{tickers[i]}/{tickers[j]}",
            "ticker_a": tickers[i],
            "ticker_b": tickers[j],
            "series": [
                {"date": idx.date().isoformat(), "value": round(float(v), 4)}
                for idx, v in rc.items()
            ],
        })

    return {
        "tickers": tickers,
        "static_matrix": static,
        "rolling_correlations": rolling,
    }


def engle_granger_test(
    series_a: pd.Series, series_b: pd.Series
) -> dict:
    """
    Two-step Engle-Granger cointegration test.

    1. Regress series_a on series_b via OLS.
    2. Test the residuals for a unit root using ADF (manual implementation).

    Returns dict with regression params, ADF statistic, p-value, and
    whether the pair is cointegrated at the 5% level.
    """
    a = series_a.values.astype(float)
    b = series_b.values.astype(float)

    # OLS: a = alpha + beta * b + epsilon
    X = np.column_stack([np.ones(len(b)), b])
    betas, _, _, _ = np.linalg.lstsq(X, a, rcond=None)
    alpha, beta = float(betas[0]), float(betas[1])
    residuals = a - (alpha + beta * b)

    # ADF test on residuals (Dickey-Fuller with one lag)
    adf_stat, adf_pvalue = _adf_test(residuals)

    return {
        "alpha": round(alpha, 6),
        "beta": round(beta, 6),
        "adf_statistic": round(adf_stat, 4),
        "adf_pvalue": round(adf_pvalue, 4),
        "cointegrated": adf_pvalue < 0.05,
    }


def _adf_test(x: np.ndarray, max_lags: int = 1) -> tuple[float, float]:
    """
    Augmented Dickey-Fuller test (OLS-based, no statsmodels dependency).

    Tests H0: unit root present (non-stationary).
    Returns (t-statistic, approximate p-value).
    """
    n = len(x)
    dx = np.diff(x)
    x_lag = x[max_lags:-1] if max_lags > 0 else x[:-1]
    dx_dep = dx[max_lags:]

    # Build design: [x_{t-1}, Δx_{t-1}, ..., Δx_{t-p}, intercept]
    cols = [x_lag]
    for lag in range(1, max_lags + 1):
        cols.append(dx[max_lags - lag : n - 1 - lag])
    cols.append(np.ones(len(dx_dep)))
    X = np.column_stack(cols)

    betas, _, _, _ = np.linalg.lstsq(X, dx_dep, rcond=None)
    resid = dx_dep - X @ betas

    n_obs = len(dx_dep)
    k = X.shape[1]
    sigma2 = np.sum(resid ** 2) / max(n_obs - k, 1)
    xtx_inv = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(xtx_inv) * sigma2)

    gamma = betas[0]
    t_stat = float(gamma / se[0]) if se[0] > 0 else 0.0

    # Approximate p-value using MacKinnon critical values (n=∞, case=c)
    # Critical values: 1% = -3.43, 5% = -2.86, 10% = -2.57
    if t_stat < -3.43:
        p = 0.005
    elif t_stat < -2.86:
        p = 0.01 + (t_stat - (-3.43)) / ((-2.86) - (-3.43)) * (0.05 - 0.01)
    elif t_stat < -2.57:
        p = 0.05 + (t_stat - (-2.86)) / ((-2.57) - (-2.86)) * (0.10 - 0.05)
    elif t_stat < -1.94:
        p = 0.10 + (t_stat - (-2.57)) / ((-1.94) - (-2.57)) * (0.30 - 0.10)
    elif t_stat < -1.62:
        p = 0.30 + (t_stat - (-1.94)) / ((-1.62) - (-1.94)) * (0.50 - 0.30)
    else:
        p = min(0.50 + (t_stat - (-1.62)) * 0.15, 1.0)

    return t_stat, max(0.0, min(p, 1.0))


def compute_spread(
    series_a: pd.Series,
    series_b: pd.Series,
    lookback: int = 63,
) -> dict:
    """
    Compute the log-price-ratio spread between two series, with a rolling
    z-score for mean-reversion signal generation.

    Also estimates the Ornstein-Uhlenbeck half-life of mean reversion.
    """
    a = np.log(series_a.astype(float))
    b = np.log(series_b.astype(float))
    spread = a - b

    rolling_mean = spread.rolling(lookback).mean()
    rolling_std = spread.rolling(lookback).std()
    z_score = ((spread - rolling_mean) / rolling_std.replace(0, np.nan)).dropna()

    half_life = _half_life(spread.dropna().values)

    spread_clean = spread.dropna()
    return {
        "spread_series": [
            {"date": idx.date().isoformat(), "value": round(float(v), 6)}
            for idx, v in spread_clean.items()
        ],
        "zscore_series": [
            {"date": idx.date().isoformat(), "value": round(float(v), 4)}
            for idx, v in z_score.items()
        ],
        "half_life_days": round(half_life, 1) if half_life and half_life > 0 else None,
        "current_zscore": round(float(z_score.iloc[-1]), 4) if len(z_score) > 0 else None,
        "spread_mean": round(float(spread_clean.mean()), 6),
        "spread_std": round(float(spread_clean.std()), 6),
    }


def _half_life(spread: np.ndarray) -> float | None:
    """
    Estimate the half-life of mean reversion via AR(1) regression on the spread.

    spread_t = phi * spread_{t-1} + epsilon
    half_life = -ln(2) / ln(phi)
    """
    if len(spread) < 10:
        return None

    y = spread[1:]
    x = spread[:-1]

    X = np.column_stack([x, np.ones(len(x))])
    betas, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    phi = betas[0]

    if phi <= 0 or phi >= 1:
        return None

    return -np.log(2) / np.log(phi)


def discover_pairs(
    prices: dict[str, pd.Series],
    max_pairs: int = 10,
) -> list[dict]:
    """
    Test all ticker pairs for cointegration and return the top candidates
    ranked by ADF p-value (lowest = strongest evidence of cointegration).
    """
    tickers = list(prices.keys())
    if len(tickers) < 2:
        return []

    df = pd.DataFrame(prices).sort_index().dropna()
    if len(df) < 60:
        return []

    results = []
    for ta, tb in combinations(tickers, 2):
        try:
            eg = engle_granger_test(df[ta], df[tb])
            spread_info = compute_spread(df[ta], df[tb])
            results.append({
                "ticker_a": ta,
                "ticker_b": tb,
                "adf_statistic": eg["adf_statistic"],
                "adf_pvalue": eg["adf_pvalue"],
                "cointegrated": eg["cointegrated"],
                "beta": eg["beta"],
                "half_life_days": spread_info["half_life_days"],
                "current_zscore": spread_info["current_zscore"],
                "spread_std": spread_info["spread_std"],
            })
        except Exception:
            continue

    results.sort(key=lambda r: r["adf_pvalue"])
    return results[:max_pairs]
