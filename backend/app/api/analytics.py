"""
POST /api/analytics/compare              — Compare multiple backtest results
POST /api/analytics/monte-carlo/{id}     — Run Monte Carlo simulation
GET  /api/analytics/export/{id}          — Export results as CSV
POST /api/analytics/portfolio-blend      — Blend multiple backtests with weights
POST /api/analytics/correlation          — Correlation matrix & cointegration analysis
POST /api/analytics/spread              — Spread & z-score for a specific pair
"""

from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_workspace
from app.database import get_db
from app.models.auth import Workspace
from app.schemas.analytics import (
    CapacityResponse,
    CompareRequest,
    ComparisonResponse,
    CorrelationRequest,
    CorrelationResponse,
    FactorExposureResponse,
    MonteCarloResult,
    PortfolioBlendRequest,
    PortfolioBlendResponse,
    RegimeAnalysisResponse,
    RiskBudgetResponse,
    SpreadRequest,
    SpreadResponse,
    TransactionCostAnalysisResponse,
)
from app.schemas.common import ErrorResponse
from app.services.analytics import compute_all_metrics, compute_monte_carlo
from app.services.analytics_backtests import (
    aligned_equity_frame,
    backtest_equity_series,
    backtest_returns_series,
    benchmark_series,
    build_backtest_export_csv,
    load_backtest_run_or_404,
    load_backtest_runs_or_404,
    load_backtest_trades,
    resolve_blend_weights,
)
from app.services.risk_budget import build_risk_budget_report

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post(
    "/risk-budget/{backtest_id}",
    response_model=RiskBudgetResponse,
    summary="Build a risk budgeting dashboard",
    description=(
        "Reconstructs the latest non-flat portfolio snapshot from a saved backtest, "
        "decomposes one-day VaR / CVaR by position, and stress-tests that book "
        "through 2008, COVID, and 2022 rate-shock regimes."
    ),
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def risk_budget_analysis(
    backtest_id: str,
    lookback_days: int = Query(63, ge=21, le=252),
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    run = await load_backtest_run_or_404(db, backtest_id, current_workspace.id)
    trades = await load_backtest_trades(
        db,
        backtest_id,
        workspace_id=current_workspace.id,
    )
    return await build_risk_budget_report(
        db=db,
        run=run,
        trades=trades,
        lookback_days=lookback_days,
    )


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    summary="Compare multiple backtests",
    description=(
        "Loads multiple saved backtests, aligns their equity curves, and returns "
        "a comparison bundle including the return-correlation matrix."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "At least two backtests are required.",
        },
        404: {
            "model": ErrorResponse,
            "description": "One of the requested backtests was not found.",
        },
    },
)
async def compare_backtests(
    payload: CompareRequest,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    ids = payload.backtest_ids
    if len(ids) < 2:
        raise HTTPException(400, "Need at least 2 backtests to compare")

    results = await load_backtest_runs_or_404(db, ids, current_workspace.id)

    # Correlation matrix from equity curves
    df = pd.concat([backtest_returns_series(run, name=run.id) for run in results], axis=1)
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


@router.post(
    "/monte-carlo/{backtest_id}",
    response_model=MonteCarloResult,
    summary="Run Monte Carlo simulation",
    description=(
        "Bootstraps historical daily returns from a saved backtest to project a "
        "distribution of potential future equity paths."
    ),
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def monte_carlo(
    backtest_id: str,
    n_simulations: int = Query(1000, ge=100, le=10000),
    n_days: int = Query(252, ge=30, le=1260),
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    run = await load_backtest_run_or_404(db, backtest_id, current_workspace.id)
    equity = backtest_equity_series(run)
    returns = equity.pct_change().dropna()

    result = compute_monte_carlo(
        returns,
        n_simulations=n_simulations,
        n_days=n_days,
        initial_value=run.initial_capital,
    )
    return result


@router.get(
    "/export/{backtest_id}",
    summary="Export a backtest as CSV",
    description=(
        "Exports configuration, performance metrics, equity curve, and monthly "
        "returns for a saved backtest in CSV format."
    ),
    responses={
        200: {
            "description": "CSV export stream.",
            "content": {
                "text/csv": {
                    "example": "=== Configuration ===\nstrategy,sma_crossover\n",
                }
            },
        },
        404: {"model": ErrorResponse, "description": "Backtest was not found."},
        501: {"model": ErrorResponse, "description": "Export format is unsupported."},
    },
)
async def export_results(
    backtest_id: str,
    format: str = Query("csv"),
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    run = await load_backtest_run_or_404(db, backtest_id, current_workspace.id)

    if format == "csv":
        return StreamingResponse(
            iter([build_backtest_export_csv(run)]),
            media_type="text/csv",
            headers={
                "Content-Disposition": (f"attachment; filename=backtest_{backtest_id[:8]}.csv")
            },
        )

    raise HTTPException(501, "Only CSV export is currently supported")


@router.post(
    "/capacity/{backtest_id}",
    response_model=CapacityResponse,
    summary="Estimate strategy capacity",
    description=(
        "Estimates how much capital a strategy can absorb before its trade size "
        "becomes an excessive share of average daily volume."
    ),
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def capacity_analysis(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    """
    Estimate strategy capacity: at what AUM does market impact erode the edge?

    For each trade, compute shares_traded / ADV. Scale to find AUM thresholds
    where the strategy would consume 1%, 5%, and 10% of average daily volume.
    """
    from datetime import date as date_cls

    from app.services.data_ingestion import get_price_dataframe

    run = await load_backtest_run_or_404(db, backtest_id, current_workspace.id)

    # Load trades
    trades = await load_backtest_trades(
        db,
        backtest_id,
        workspace_id=current_workspace.id,
    )

    if not trades:
        return {
            "message": "No trades in this backtest",
            "capacity_estimates": [],
            "trade_adv_stats": [],
        }

    start = date_cls.fromisoformat(run.start_date)
    end = date_cls.fromisoformat(run.end_date)

    # Compute ADV per ticker from price data
    adv_by_ticker: dict[str, float] = {}
    price_cache: dict[str, pd.DataFrame] = {}

    for ticker in set(t.ticker for t in trades):
        try:
            df = await get_price_dataframe(db, ticker, start, end)
            price_cache[ticker] = df
            # Dollar ADV = avg(adj_close * volume)
            dollar_vol = df["adj_close"] * df["volume"]
            adv_by_ticker[ticker] = float(dollar_vol.mean())
        except Exception:
            pass

    # For each trade, compute the ADV participation at baseline capital
    initial_capital = run.initial_capital
    trade_stats: list[dict[str, Any]] = []
    for t in trades:
        if t.ticker not in price_cache:
            continue
        # Trade dollar notional
        price = t.entry_price if t.entry_price else 0
        notional = t.shares * price
        adv = adv_by_ticker.get(t.ticker, 0)
        if adv <= 0 or notional <= 0:
            continue
        adv_participation_pct = notional / adv * 100  # % of ADV at current capital
        trade_stats.append(
            {
                "ticker": t.ticker,
                "side": t.side,
                "date": t.entry_date,
                "shares": t.shares,
                "notional": round(notional, 0),
                "adv": round(adv, 0),
                "adv_participation_pct": round(adv_participation_pct, 4),
            }
        )

    if not trade_stats:
        return {
            "message": "Could not compute ADV stats",
            "capacity_estimates": [],
            "trade_adv_stats": [],
        }

    # Sort by ADV participation (most impactful first)
    trade_stats.sort(key=lambda x: float(x["adv_participation_pct"]), reverse=True)

    # Capacity scaling: at what AUM scale does max ADV participation reach threshold?
    # If strategy uses X% of ADV at current capital C, then at scale S×C it uses X*S%
    # Capacity at T% threshold = T / max_participation * initial_capital
    participations = [float(t["adv_participation_pct"]) for t in trade_stats]
    max_participation = max(participations, default=0.0)
    avg_participation = float(np.mean(participations))
    p90_participation = float(np.percentile(participations, 90))

    thresholds = [1.0, 5.0, 10.0]
    capacity_estimates = []
    for thresh in thresholds:
        capacity_aum = (
            thresh / max_participation * initial_capital if max_participation > 0 else None
        )
        capacity_estimates.append(
            {
                "adv_threshold_pct": thresh,
                "capacity_aum": round(capacity_aum) if capacity_aum else None,
                "label": f"Max trade uses ≤{thresh}% of ADV",
            }
        )

    return {
        "initial_capital": initial_capital,
        "n_trades": len(trade_stats),
        "max_adv_participation_pct": round(max_participation, 4),
        "avg_adv_participation_pct": round(avg_participation, 4),
        "p90_adv_participation_pct": round(p90_participation, 4),
        "capacity_estimates": capacity_estimates,
        "trade_adv_stats": trade_stats[:20],  # top 20 most impactful
    }


@router.post(
    "/tca/{backtest_id}",
    response_model=TransactionCostAnalysisResponse,
    summary="Analyze transaction costs",
    description=(
        "Aggregates commissions, spread, impact, timing, opportunity costs, "
        "and fill-quality metrics for a saved backtest."
    ),
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def transaction_cost_analysis(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    run = await load_backtest_run_or_404(db, backtest_id, current_workspace.id)
    trades = await load_backtest_trades(
        db,
        backtest_id,
        workspace_id=current_workspace.id,
    )
    model = {
        "market_impact_model": run.market_impact_model or "almgren_chriss",
        "max_volume_participation_pct": run.max_volume_participation_pct or 5,
        "slippage_bps": run.slippage_bps,
        "commission_per_share": run.commission_per_share,
    }
    if not trades:
        return {
            "message": "No trades in this backtest",
            "model": model,
            "summary": {
                "total_trades": 0,
                "total_commission": 0.0,
                "total_spread_cost": 0.0,
                "total_market_impact_cost": 0.0,
                "total_timing_cost": 0.0,
                "total_opportunity_cost": 0.0,
                "total_borrow_cost": 0.0,
                "total_locate_fees": 0.0,
                "total_implementation_shortfall": 0.0,
                "avg_fill_rate_pct": 0.0,
                "avg_participation_rate_pct": 0.0,
                "p90_participation_rate_pct": 0.0,
                "cost_as_pct_of_initial_capital": 0.0,
            },
            "ticker_breakdown": [],
            "top_cost_trades": [],
        }

    def _fill_rate(trade: Any) -> float:
        requested = trade.requested_shares or trade.shares
        return (trade.shares / max(requested, 1)) * 100

    summary = {
        "total_trades": len(trades),
        "total_commission": round(sum(trade.commission for trade in trades), 2),
        "total_spread_cost": round(sum(trade.spread_cost for trade in trades), 2),
        "total_market_impact_cost": round(sum(trade.market_impact_cost for trade in trades), 2),
        "total_timing_cost": round(sum(trade.timing_cost for trade in trades), 2),
        "total_opportunity_cost": round(sum(trade.opportunity_cost for trade in trades), 2),
        "total_borrow_cost": round(sum(trade.borrow_cost for trade in trades), 2),
        "total_locate_fees": round(sum(trade.locate_fee for trade in trades), 2),
        "total_implementation_shortfall": round(
            sum(trade.implementation_shortfall for trade in trades), 2
        ),
        "avg_fill_rate_pct": round(float(np.mean([_fill_rate(trade) for trade in trades])), 2),
        "avg_participation_rate_pct": round(
            float(np.mean([trade.participation_rate_pct for trade in trades])), 3
        ),
        "p90_participation_rate_pct": round(
            float(np.percentile([trade.participation_rate_pct for trade in trades], 90)),
            3,
        ),
        "cost_as_pct_of_initial_capital": round(
            (
                sum(trade.implementation_shortfall for trade in trades)
                / max(run.initial_capital, 1e-8)
            )
            * 100,
            3,
        ),
    }

    ticker_map: dict[str, dict] = {}
    for trade in trades:
        row = ticker_map.setdefault(
            trade.ticker,
            {
                "ticker": trade.ticker,
                "trades": 0,
                "total_commission": 0.0,
                "total_spread_cost": 0.0,
                "total_market_impact_cost": 0.0,
                "total_timing_cost": 0.0,
                "total_opportunity_cost": 0.0,
                "total_implementation_shortfall": 0.0,
                "fill_rates": [],
                "participation_rates": [],
            },
        )
        row["trades"] += 1
        row["total_commission"] += trade.commission
        row["total_spread_cost"] += trade.spread_cost
        row["total_market_impact_cost"] += trade.market_impact_cost
        row["total_timing_cost"] += trade.timing_cost
        row["total_opportunity_cost"] += trade.opportunity_cost
        row["total_implementation_shortfall"] += trade.implementation_shortfall
        row["fill_rates"].append(_fill_rate(trade))
        row["participation_rates"].append(trade.participation_rate_pct)

    ticker_breakdown = []
    for row in ticker_map.values():
        ticker_breakdown.append(
            {
                "ticker": row["ticker"],
                "trades": row["trades"],
                "total_commission": round(row["total_commission"], 2),
                "total_spread_cost": round(row["total_spread_cost"], 2),
                "total_market_impact_cost": round(row["total_market_impact_cost"], 2),
                "total_timing_cost": round(row["total_timing_cost"], 2),
                "total_opportunity_cost": round(row["total_opportunity_cost"], 2),
                "total_implementation_shortfall": round(row["total_implementation_shortfall"], 2),
                "avg_fill_rate_pct": round(float(np.mean(row["fill_rates"])), 2),
                "avg_participation_rate_pct": round(float(np.mean(row["participation_rates"])), 3),
            }
        )

    ticker_breakdown.sort(key=lambda row: row["total_implementation_shortfall"], reverse=True)

    top_cost_trades = [
        {
            "id": trade.id,
            "ticker": trade.ticker,
            "side": trade.side,
            "position_direction": trade.position_direction,
            "date": trade.exit_date or trade.entry_date,
            "shares": trade.shares,
            "requested_shares": trade.requested_shares,
            "unfilled_shares": trade.unfilled_shares,
            "commission": trade.commission,
            "spread_cost": trade.spread_cost,
            "market_impact_cost": trade.market_impact_cost,
            "timing_cost": trade.timing_cost,
            "opportunity_cost": trade.opportunity_cost,
            "implementation_shortfall": trade.implementation_shortfall,
            "fill_rate_pct": round(_fill_rate(trade), 2),
            "participation_rate_pct": round(trade.participation_rate_pct, 3),
            "risk_event": trade.risk_event,
        }
        for trade in sorted(trades, key=lambda trade: trade.implementation_shortfall, reverse=True)[
            :15
        ]
    ]

    return {
        "model": model,
        "summary": summary,
        "ticker_breakdown": ticker_breakdown,
        "top_cost_trades": top_cost_trades,
    }


@router.post(
    "/regime-analysis/{backtest_id}",
    response_model=RegimeAnalysisResponse,
    summary="Run regime analysis",
    description=(
        "Classifies the benchmark environment into trend, chop, high-volatility, "
        "and neutral regimes, then summarizes strategy performance inside each regime."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Backtest was not found."},
        422: {
            "model": ErrorResponse,
            "description": "Required market data could not be loaded.",
        },
    },
)
async def regime_analysis(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
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
    from datetime import date as date_cls

    from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe

    run = await load_backtest_run_or_404(db, backtest_id, current_workspace.id)

    start = date_cls.fromisoformat(run.start_date)
    end = date_cls.fromisoformat(run.end_date)
    benchmark_ticker = run.benchmark or "SPY"

    # Load benchmark OHLCV for ADX calculation
    loaded = await ensure_data_loaded(db, benchmark_ticker, start, end)
    if not loaded:
        raise HTTPException(422, f"Could not load {benchmark_ticker} data")

    bench_df = await get_price_dataframe(db, benchmark_ticker, start, end)

    # Strategy equity
    strat_series = backtest_equity_series(run)
    strat_returns = strat_series.pct_change().dropna()

    # Compute ADX (14-period)
    high = bench_df["high"]
    low = bench_df["low"]
    close = bench_df["close"]

    # True Range
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # Directional movements
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    dm_plus = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    dm_minus = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    period = 14
    atr = tr.ewm(span=period, adjust=False).mean()
    di_plus = 100 * pd.Series(dm_plus, index=high.index).ewm(span=period, adjust=False).mean() / atr
    di_minus = (
        100 * pd.Series(dm_minus, index=high.index).ewm(span=period, adjust=False).mean() / atr
    )

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

    stats: list[dict[str, Any]] = []
    for regime in regime_order:
        rets = regime_groups.get(regime, [])
        if not rets:
            continue
        arr = np.array(rets)
        ann_ret = float(np.mean(arr)) * 252 * 100
        ann_vol = float(np.std(arr, ddof=1)) * np.sqrt(252) * 100 if len(arr) > 1 else 0
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
        stats.append(
            {
                "regime": regime,
                "color": regime_colors[regime],
                "days": len(rets),
                "pct_of_period": round(len(rets) / len(timeline) * 100, 1) if timeline else 0,
                "ann_return_pct": round(ann_ret, 2),
                "ann_volatility_pct": round(ann_vol, 2),
                "sharpe": round(sharpe, 3),
            }
        )

    # ADX description
    desc = ""
    trending_pct = float(
        next((s["pct_of_period"] for s in stats if s["regime"] == "Trending"), 0.0)
    )
    choppy_pct = float(next((s["pct_of_period"] for s in stats if s["regime"] == "Choppy"), 0.0))
    if trending_pct > 40:
        desc = "The backtest period was predominantly trending — strategy likely benefits from directional positions."
    elif choppy_pct > 40:
        desc = "The backtest period was predominantly choppy — mean-reversion strategies should outperform trend-following."
    else:
        desc = "Mixed regime environment — strategy performance may vary across sub-periods."

    return {
        "timeline": timeline,
        "regime_stats": stats,
        "description": desc,
    }


@router.post(
    "/factor-exposure/{backtest_id}",
    response_model=FactorExposureResponse,
    summary="Estimate factor exposures",
    description=(
        "Runs a multi-factor regression of strategy returns against market, size, "
        "value, and momentum proxies."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Backtest was not found."},
        422: {
            "model": ErrorResponse,
            "description": "Insufficient or missing factor data.",
        },
        500: {
            "model": ErrorResponse,
            "description": "Regression could not be completed.",
        },
    },
)
async def factor_exposure(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
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
    from datetime import date as date_cls

    from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe

    run = await load_backtest_run_or_404(db, backtest_id, current_workspace.id)

    start = date_cls.fromisoformat(run.start_date)
    end = date_cls.fromisoformat(run.end_date)

    # Strategy returns
    strategy_series = backtest_equity_series(run)
    strategy_returns = strategy_series.pct_change().dropna()

    # Fetch factor proxies (best-effort; skip if yfinance fails)
    factor_tickers = {
        "Market": "SPY",
        "Size": "IWM",
        "Value": "VTV",
        "Momentum": "MTUM",
    }
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
        if label in factor_prices:
            factor_returns[label] = (
                factor_prices[label].pct_change() - spy_prices.pct_change()
            ).dropna()

    # Align all series
    factor_df = pd.DataFrame(factor_returns)
    aligned = pd.concat([strategy_returns.rename("Strategy"), factor_df], axis=1).dropna()

    if len(aligned) < 30:
        raise HTTPException(
            422, "Insufficient overlapping data for factor regression (need ≥30 days)"
        )

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
        sigma2 = np.sum(resid**2) / max(n - k, 1)
        xtx_inv = np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(xtx_inv) * sigma2)
        t_stats = betas / np.where(se > 0, se, np.nan)
        p_values = 2 * (1 - t_dist.cdf(np.abs(t_stats), df=max(n - k, 1)))
        ss_res = np.sum(resid**2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    except Exception as e:
        raise HTTPException(500, f"Regression failed: {e}")

    result: dict[str, Any] = {
        "alpha_annualized": round(float(betas[0]) * 252 * 100, 4),
        "r_squared": round(float(r2), 4),
        "n_obs": int(n),
        "factors": [],
    }

    for i, factor in enumerate(factor_cols):
        result["factors"].append(
            {
                "name": factor,
                "beta": round(float(betas[i + 1]), 4),
                "t_stat": round(float(t_stats[i + 1]), 3),
                "p_value": round(float(p_values[i + 1]), 4),
                "significant": bool(p_values[i + 1] < 0.05),
            }
        )

    return result


@router.post(
    "/portfolio-blend",
    response_model=PortfolioBlendResponse,
    summary="Blend multiple backtests into a portfolio",
    description=(
        "Combines multiple saved backtests using custom or optimized weights and "
        "returns a portfolio-level equity curve, metrics, and contribution breakdown."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "At least two backtests are required.",
        },
        404: {
            "model": ErrorResponse,
            "description": "One of the requested backtests was not found.",
        },
    },
)
async def portfolio_blend(
    payload: PortfolioBlendRequest,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    """
    Blend multiple backtests by weights and return portfolio equity + metrics.

    payload: { backtest_ids: [...], weights: [...], optimize: "equal"|"max_sharpe"|"min_dd" }
    """
    ids = payload.backtest_ids
    weights_in = payload.weights
    optimize = payload.optimize

    if len(ids) < 2:
        raise HTTPException(400, "Need at least 2 backtests to blend")

    runs = await load_backtest_runs_or_404(db, ids, current_workspace.id)

    # Align equity curves to common dates
    df = aligned_equity_frame(
        runs,
        normalize_to=1.0,
        column_names=list(range(len(runs))),
    )

    returns = df.pct_change().dropna()
    weights = resolve_blend_weights(returns, df, optimize, weights_in)

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
    bench_series = benchmark_series(runs[0])
    # Normalize benchmark to same scale
    if not bench_series.empty:
        bench_series = bench_series / bench_series.iloc[0] * initial_capital

    metrics = compute_all_metrics(portfolio_equity, bench_series, initial_capital)

    # Per-asset contribution (return attribution)
    asset_contribs = []
    for i, run in enumerate(runs):
        asset_return = float(df.iloc[-1, i] / df.iloc[0, i] - 1) * 100
        asset_contribs.append(
            {
                "id": run.id,
                "strategy_id": run.strategy_id,
                "tickers": run.tickers,
                "weight": round(float(weights[i]), 4),
                "asset_return_pct": round(asset_return, 2),
                "contribution_pct": round(asset_return * float(weights[i]), 2),
            }
        )

    return {
        "weights": [round(float(w), 4) for w in weights],
        "optimize": optimize,
        "equity_curve": equity_curve,
        "metrics": metrics,
        "asset_contributions": asset_contribs,
    }


# ---------------------------------------------------------------------------
# Correlation & cointegration
# ---------------------------------------------------------------------------


@router.post(
    "/correlation",
    response_model=CorrelationResponse,
    summary="Correlation matrix & cointegration analysis",
    description=(
        "Loads OHLCV data for the requested tickers, computes a static "
        "correlation matrix, rolling pairwise correlations, and runs "
        "Engle-Granger cointegration tests to discover tradeable pairs."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request parameters."},
        422: {
            "model": ErrorResponse,
            "description": "Could not load data for one or more tickers.",
        },
    },
)
async def correlation_analysis(
    payload: CorrelationRequest,
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_cls

    from app.services.cointegration import (
        compute_correlation_matrix,
        discover_pairs,
    )
    from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe

    start = date_cls.fromisoformat(payload.start_date)
    end = date_cls.fromisoformat(payload.end_date)

    # Load price data for all tickers
    prices: dict[str, pd.Series] = {}
    failed: list[str] = []
    for ticker in payload.tickers:
        loaded = await ensure_data_loaded(db, ticker, start, end)
        if not loaded:
            failed.append(ticker)
            continue
        df = await get_price_dataframe(db, ticker, start, end)
        if df.empty:
            failed.append(ticker)
            continue
        prices[ticker] = df["close"]

    if failed:
        raise HTTPException(422, f"Could not load data for: {', '.join(failed)}")
    if len(prices) < 2:
        raise HTTPException(400, "Need at least 2 tickers with available data")

    try:
        corr = compute_correlation_matrix(prices, payload.rolling_window)
    except ValueError as e:
        raise HTTPException(400, str(e))

    pairs = discover_pairs(prices, payload.max_pairs)

    return {
        "tickers": corr["tickers"],
        "static_matrix": corr["static_matrix"],
        "rolling_correlations": corr["rolling_correlations"],
        "discovered_pairs": pairs,
    }


@router.post(
    "/spread",
    response_model=SpreadResponse,
    summary="Spread analysis for a ticker pair",
    description=(
        "Computes the log-price-ratio spread, rolling z-score, half-life of "
        "mean reversion, and Engle-Granger cointegration test for a specific pair."
    ),
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Could not load data for one or both tickers.",
        },
    },
)
async def spread_analysis(
    payload: SpreadRequest,
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_cls

    from app.services.cointegration import compute_spread, engle_granger_test
    from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe

    start = date_cls.fromisoformat(payload.start_date)
    end = date_cls.fromisoformat(payload.end_date)

    for ticker in [payload.ticker_a, payload.ticker_b]:
        loaded = await ensure_data_loaded(db, ticker, start, end)
        if not loaded:
            raise HTTPException(422, f"Could not load data for {ticker}")

    df_a = await get_price_dataframe(db, payload.ticker_a, start, end)
    df_b = await get_price_dataframe(db, payload.ticker_b, start, end)

    if df_a.empty or df_b.empty:
        raise HTTPException(422, "Insufficient price data for one or both tickers")

    # Align on common dates
    combined = pd.DataFrame(
        {
            payload.ticker_a: df_a["close"],
            payload.ticker_b: df_b["close"],
        }
    ).dropna()

    if len(combined) < payload.lookback:
        raise HTTPException(
            400,
            f"Only {len(combined)} overlapping days — need at least {payload.lookback}",
        )

    sa = combined[payload.ticker_a]
    sb = combined[payload.ticker_b]

    spread = compute_spread(sa, sb, payload.lookback)
    coint = engle_granger_test(sa, sb)

    return {
        "ticker_a": payload.ticker_a,
        "ticker_b": payload.ticker_b,
        **spread,
        "cointegration": {
            "ticker_a": payload.ticker_a,
            "ticker_b": payload.ticker_b,
            "adf_statistic": coint["adf_statistic"],
            "adf_pvalue": coint["adf_pvalue"],
            "cointegrated": coint["cointegrated"],
            "beta": coint["beta"],
            "half_life_days": spread["half_life_days"],
            "current_zscore": spread["current_zscore"],
            "spread_std": spread["spread_std"],
        },
    }
