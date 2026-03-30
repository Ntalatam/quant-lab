"""
POST /api/analytics/compare              — Compare multiple backtest results
POST /api/analytics/monte-carlo/{id}     — Run Monte Carlo simulation
GET  /api/analytics/export/{id}          — Export results as CSV
POST /api/analytics/portfolio-blend      — Blend multiple backtests with weights
"""

import csv
import io

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.backtest import BacktestRun
from app.services.analytics import compute_monte_carlo, compute_all_metrics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/compare")
async def compare_backtests(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    ids = payload.get("backtest_ids", [])
    if len(ids) < 2:
        raise HTTPException(400, "Need at least 2 backtests to compare")

    results = []
    for bid in ids:
        r = await db.execute(select(BacktestRun).where(BacktestRun.id == bid))
        run = r.scalar_one_or_none()
        if not run:
            raise HTTPException(404, f"Backtest {bid} not found")
        results.append(run)

    # Correlation matrix from equity curves
    curves = {}
    for run in results:
        series = (
            pd.Series(
                [p["value"] for p in run.equity_curve],
                index=pd.to_datetime([p["date"] for p in run.equity_curve]),
            )
            .pct_change()
            .dropna()
        )
        curves[run.id] = series

    df = pd.DataFrame(curves)
    corr = df.corr().values.tolist()

    return {
        "backtests": [
            {
                "id": r.id,
                "strategy_id": r.strategy_id,
                "tickers": r.tickers,
                "metrics": r.metrics,
                "equity_curve": r.equity_curve,
            }
            for r in results
        ],
        "correlation_matrix": corr,
    }


@router.post("/monte-carlo/{backtest_id}")
async def monte_carlo(
    backtest_id: str,
    n_simulations: int = Query(1000, ge=100, le=10000),
    n_days: int = Query(252, ge=30, le=1260),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(BacktestRun).where(BacktestRun.id == backtest_id)
    )
    run = r.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    equity = pd.Series(
        [p["value"] for p in run.equity_curve],
        index=pd.to_datetime([p["date"] for p in run.equity_curve]),
    )
    returns = equity.pct_change().dropna()

    result = compute_monte_carlo(
        returns,
        n_simulations=n_simulations,
        n_days=n_days,
        initial_value=run.initial_capital,
    )
    return result


@router.get("/export/{backtest_id}")
async def export_results(
    backtest_id: str,
    format: str = Query("csv"),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(BacktestRun).where(BacktestRun.id == backtest_id)
    )
    run = r.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["=== Configuration ==="])
        writer.writerow(["strategy", run.strategy_id])
        writer.writerow(["tickers", ", ".join(run.tickers)])
        writer.writerow(["period", f"{run.start_date} to {run.end_date}"])
        writer.writerow(["initial_capital", run.initial_capital])
        writer.writerow([])

        writer.writerow(["=== Performance Metrics ==="])
        for key, value in run.metrics.items():
            writer.writerow([key, value])

        writer.writerow([])
        writer.writerow(["=== Equity Curve ==="])
        writer.writerow(["date", "equity"])
        for pt in run.equity_curve:
            writer.writerow([pt["date"], pt["value"]])

        writer.writerow([])
        writer.writerow(["=== Monthly Returns ==="])
        writer.writerow(["year", "month", "return_pct"])
        for mr in run.monthly_returns:
            writer.writerow([mr["year"], mr["month"], mr["return_pct"]])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=backtest_{backtest_id[:8]}.csv"
                )
            },
        )

    raise HTTPException(501, "Only CSV export is currently supported")


@router.post("/regime-analysis/{backtest_id}")
async def regime_analysis(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Classify market regimes using rolling ADX and volatility.

    Regimes:
      - High Volatility: rolling 21-day vol > 1.5× long-run average
      - Trending: ADX > 25
      - Choppy: ADX < 15
      - Neutral: otherwise

    Returns per-date regime labels and per-regime performance stats.
    """
    from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe
    from datetime import date as date_cls

    r = await db.execute(select(BacktestRun).where(BacktestRun.id == backtest_id))
    run = r.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    start = date_cls.fromisoformat(run.start_date)
    end = date_cls.fromisoformat(run.end_date)
    benchmark_ticker = run.benchmark or "SPY"

    # Load benchmark OHLCV for ADX calculation
    loaded = await ensure_data_loaded(db, benchmark_ticker, start, end)
    if not loaded:
        raise HTTPException(422, f"Could not load {benchmark_ticker} data")

    bench_df = await get_price_dataframe(db, benchmark_ticker, start, end)

    # Strategy equity
    strat_series = pd.Series(
        [p["value"] for p in run.equity_curve],
        index=pd.to_datetime([p["date"] for p in run.equity_curve]),
    )
    strat_returns = strat_series.pct_change().dropna()

    # Compute ADX (14-period)
    high = bench_df["high"]
    low = bench_df["low"]
    close = bench_df["close"]

    # True Range
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    # Directional movements
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    dm_plus = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    dm_minus = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    period = 14
    atr = tr.ewm(span=period, adjust=False).mean()
    di_plus = 100 * pd.Series(dm_plus, index=high.index).ewm(span=period, adjust=False).mean() / atr
    di_minus = 100 * pd.Series(dm_minus, index=high.index).ewm(span=period, adjust=False).mean() / atr

    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx = dx.ewm(span=period, adjust=False).mean()

    # Rolling volatility (21-day annualized)
    bench_returns = close.pct_change().dropna()
    rolling_vol = bench_returns.rolling(21).std() * np.sqrt(252)
    avg_vol = rolling_vol.mean()

    # Classify regimes
    def classify(date_idx):
        rv = rolling_vol.get(date_idx)
        adx_val = adx.get(date_idx)
        if rv is None or adx_val is None or pd.isna(rv) or pd.isna(adx_val):
            return "Neutral"
        if rv > avg_vol * 1.5:
            return "High Volatility"
        if adx_val > 25:
            return "Trending"
        if adx_val < 15:
            return "Choppy"
        return "Neutral"

    # Build timeline
    timeline = []
    for dt, ret in strat_returns.items():
        regime = classify(dt)
        timeline.append({"date": dt.date().isoformat(), "regime": regime, "return": float(ret)})

    # Per-regime stats
    regime_groups: dict[str, list[float]] = {}
    for row in timeline:
        regime_groups.setdefault(row["regime"], []).append(row["return"])

    regime_order = ["Trending", "Choppy", "High Volatility", "Neutral"]
    regime_colors = {
        "Trending": "#4488ff",
        "Choppy": "#ffcc44",
        "High Volatility": "#ff4757",
        "Neutral": "#888898",
    }

    stats = []
    for regime in regime_order:
        rets = regime_groups.get(regime, [])
        if not rets:
            continue
        arr = np.array(rets)
        ann_ret = float(np.mean(arr)) * 252 * 100
        ann_vol = float(np.std(arr, ddof=1)) * np.sqrt(252) * 100 if len(arr) > 1 else 0
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
        stats.append({
            "regime": regime,
            "color": regime_colors[regime],
            "days": len(rets),
            "pct_of_period": round(len(rets) / len(timeline) * 100, 1) if timeline else 0,
            "ann_return_pct": round(ann_ret, 2),
            "ann_volatility_pct": round(ann_vol, 2),
            "sharpe": round(sharpe, 3),
        })

    # ADX description
    desc = ""
    trending_pct = next((s["pct_of_period"] for s in stats if s["regime"] == "Trending"), 0)
    if trending_pct > 40:
        desc = "The backtest period was predominantly trending — strategy likely benefits from directional positions."
    elif next((s["pct_of_period"] for s in stats if s["regime"] == "Choppy"), 0) > 40:
        desc = "The backtest period was predominantly choppy — mean-reversion strategies should outperform trend-following."
    else:
        desc = "Mixed regime environment — strategy performance may vary across sub-periods."

    return {
        "timeline": timeline,
        "regime_stats": stats,
        "description": desc,
    }


@router.post("/factor-exposure/{backtest_id}")
async def factor_exposure(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Compute factor exposure via multi-factor regression.

    Factors:
      - Market: SPY (or benchmark) return
      - Size: IWM - SPY (small-cap premium proxy)
      - Value: VTV - VUG (value vs growth proxy)
      - Momentum: MTUM - SPY

    Returns alpha, factor betas, t-stats, p-values, R-squared.
    """
    from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe
    from datetime import date as date_cls

    r = await db.execute(select(BacktestRun).where(BacktestRun.id == backtest_id))
    run = r.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    start = date_cls.fromisoformat(run.start_date)
    end = date_cls.fromisoformat(run.end_date)

    # Strategy returns
    strategy_series = pd.Series(
        [p["value"] for p in run.equity_curve],
        index=pd.to_datetime([p["date"] for p in run.equity_curve]),
    )
    strategy_returns = strategy_series.pct_change().dropna()

    # Fetch factor proxies (best-effort; skip if yfinance fails)
    factor_tickers = {"Market": "SPY", "Size": "IWM", "Value": "VTV", "Momentum": "MTUM"}
    factor_prices: dict[str, pd.Series] = {}
    spy_prices: pd.Series | None = None

    for label, ticker in factor_tickers.items():
        try:
            loaded = await ensure_data_loaded(db, ticker, start, end)
            if loaded:
                df = await get_price_dataframe(db, ticker, start, end)
                s = pd.Series(
                    df["adj_close"].values,
                    index=df.index,
                    name=label,
                )
                if label == "Market":
                    spy_prices = s
                factor_prices[label] = s
        except Exception:
            pass

    if "Market" not in factor_prices or spy_prices is None:
        raise HTTPException(422, "Could not load market factor data (SPY). Load SPY data first.")

    # Build factor returns
    factor_returns: dict[str, pd.Series] = {}
    factor_returns["Market"] = factor_prices["Market"].pct_change().dropna()

    for label in ["Size", "Value", "Momentum"]:
        if label in factor_prices and spy_prices is not None:
            factor_returns[label] = (
                factor_prices[label].pct_change() - spy_prices.pct_change()
            ).dropna()

    # Align all series
    factor_df = pd.DataFrame(factor_returns)
    aligned = pd.concat([strategy_returns.rename("Strategy"), factor_df], axis=1).dropna()

    if len(aligned) < 30:
        raise HTTPException(422, "Insufficient overlapping data for factor regression (need ≥30 days)")

    from scipy.stats import t as t_dist

    y = aligned["Strategy"].values
    factor_cols = [c for c in aligned.columns if c != "Strategy"]
    # Design matrix: intercept + factors
    X = np.column_stack([np.ones(len(y)), aligned[factor_cols].values])

    try:
        betas, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        y_hat = X @ betas
        resid = y - y_hat
        n, k = X.shape
        sigma2 = np.sum(resid ** 2) / max(n - k, 1)
        xtx_inv = np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(xtx_inv) * sigma2)
        t_stats = betas / np.where(se > 0, se, np.nan)
        p_values = 2 * (1 - t_dist.cdf(np.abs(t_stats), df=max(n - k, 1)))
        ss_res = np.sum(resid ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    except Exception as e:
        raise HTTPException(500, f"Regression failed: {e}")

    result = {
        "alpha_annualized": round(float(betas[0]) * 252 * 100, 4),
        "r_squared": round(float(r2), 4),
        "n_obs": int(n),
        "factors": [],
    }

    for i, factor in enumerate(factor_cols):
        result["factors"].append({
            "name": factor,
            "beta": round(float(betas[i + 1]), 4),
            "t_stat": round(float(t_stats[i + 1]), 3),
            "p_value": round(float(p_values[i + 1]), 4),
            "significant": bool(p_values[i + 1] < 0.05),
        })

    return result


@router.post("/portfolio-blend")
async def portfolio_blend(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Blend multiple backtests by weights and return portfolio equity + metrics.

    payload: { backtest_ids: [...], weights: [...], optimize: "equal"|"max_sharpe"|"min_dd" }
    """
    ids = payload.get("backtest_ids", [])
    weights_in = payload.get("weights", [])
    optimize = payload.get("optimize", "custom")

    if len(ids) < 2:
        raise HTTPException(400, "Need at least 2 backtests to blend")

    runs = []
    for bid in ids:
        r = await db.execute(select(BacktestRun).where(BacktestRun.id == bid))
        run = r.scalar_one_or_none()
        if not run:
            raise HTTPException(404, f"Backtest {bid} not found")
        runs.append(run)

    # Align equity curves to common dates
    series_list = []
    for run in runs:
        s = pd.Series(
            [p["value"] for p in run.equity_curve],
            index=pd.to_datetime([p["date"] for p in run.equity_curve]),
        )
        # Normalize to 1.0 start
        s = s / s.iloc[0]
        series_list.append(s)

    df = pd.concat(series_list, axis=1).ffill().dropna()
    df.columns = list(range(len(runs)))

    returns = df.pct_change().dropna()
    n = len(runs)

    if optimize == "equal":
        weights = np.array([1.0 / n] * n)
    elif optimize == "max_sharpe":
        weights = _max_sharpe_weights(returns)
    elif optimize == "min_dd":
        weights = _min_dd_weights(returns, df)
    else:
        # Use provided weights, normalize to sum to 1
        w = np.array(weights_in[:n], dtype=float)
        if w.sum() == 0:
            w = np.ones(n) / n
        weights = w / w.sum()

    # Compute portfolio equity curve
    initial_capital = runs[0].initial_capital
    portfolio_returns = (returns * weights).sum(axis=1)
    portfolio_equity = (1 + portfolio_returns).cumprod() * initial_capital

    # Align index back to dates
    equity_curve = [
        {"date": idx.date().isoformat(), "value": round(float(v), 2)}
        for idx, v in portfolio_equity.items()
    ]

    # Metrics on portfolio
    bench_series = pd.Series(
        [p["value"] for p in runs[0].benchmark_curve],
        index=pd.to_datetime([p["date"] for p in runs[0].benchmark_curve]),
    ) if runs[0].benchmark_curve else pd.Series(dtype=float)
    # Normalize benchmark to same scale
    if not bench_series.empty:
        bench_series = bench_series / bench_series.iloc[0] * initial_capital

    metrics = compute_all_metrics(portfolio_equity, bench_series, initial_capital)

    # Per-asset contribution (return attribution)
    total_return = float(portfolio_equity.iloc[-1] / portfolio_equity.iloc[0] - 1) * 100
    asset_contribs = []
    for i, run in enumerate(runs):
        asset_return = float(df.iloc[-1, i] / df.iloc[0, i] - 1) * 100
        asset_contribs.append({
            "id": run.id,
            "strategy_id": run.strategy_id,
            "tickers": run.tickers,
            "weight": round(float(weights[i]), 4),
            "asset_return_pct": round(asset_return, 2),
            "contribution_pct": round(asset_return * float(weights[i]), 2),
        })

    return {
        "weights": [round(float(w), 4) for w in weights],
        "optimize": optimize,
        "equity_curve": equity_curve,
        "metrics": metrics,
        "asset_contributions": asset_contribs,
    }


def _max_sharpe_weights(returns: pd.DataFrame) -> np.ndarray:
    """Find weights maximizing Sharpe ratio via scipy optimization."""
    from scipy.optimize import minimize

    n = returns.shape[1]
    mean_ret = returns.mean() * 252
    cov = returns.cov() * 252

    def neg_sharpe(w):
        port_ret = np.dot(w, mean_ret)
        port_vol = np.sqrt(np.dot(w, np.dot(cov.values, w)))
        return -port_ret / port_vol if port_vol > 0 else 0

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n
    result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    w = result.x
    return w / w.sum()


def _min_dd_weights(returns: pd.DataFrame, df: pd.DataFrame) -> np.ndarray:
    """Find weights minimizing maximum portfolio drawdown."""
    from scipy.optimize import minimize

    n = returns.shape[1]

    def max_dd(w):
        port_equity = (df * w).sum(axis=1)
        roll_max = port_equity.expanding().max()
        dd = (port_equity - roll_max) / roll_max
        return float(dd.min())  # most negative value = worst drawdown

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n
    result = minimize(max_dd, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    w = result.x
    return w / w.sum()
