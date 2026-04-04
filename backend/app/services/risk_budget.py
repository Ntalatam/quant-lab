from __future__ import annotations

from datetime import date
from itertools import combinations
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import BacktestRun
from app.models.trade import TradeRecord
from app.services import cache
from app.services.asset_metadata import get_ticker_sectors
from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe

VAR_Z_95 = 1.6448536269514722
DEFAULT_LOOKBACK_DAYS = 63

STRESS_SCENARIOS = [
    {
        "id": "gfc_2008",
        "name": "2008 Global Financial Crisis",
        "description": "Lehman-era equity drawdown and cross-asset liquidity shock.",
        "start_date": date(2008, 9, 1),
        "end_date": date(2008, 11, 20),
    },
    {
        "id": "covid_2020",
        "name": "COVID Crash",
        "description": "Pandemic shock from February 2020 highs to the March 2020 low.",
        "start_date": date(2020, 2, 19),
        "end_date": date(2020, 3, 23),
    },
    {
        "id": "rate_hike_2022",
        "name": "2022 Rate Hike Shock",
        "description": "Inflation-driven duration shock across equities and bonds.",
        "start_date": date(2022, 1, 3),
        "end_date": date(2022, 10, 12),
    },
]

SECTOR_PROXY_MAP = {
    "Broad Market ETF": "SPY",
    "Technology": "XLK",
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Rates ETF": "TLT",
    "Commodity ETF": "GLD",
}


async def build_risk_budget_report(
    db: AsyncSession,
    run: BacktestRun,
    trades: list[TradeRecord],
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict[str, Any]:
    cache_key = f"analytics:risk-budget:{run.id}:{lookback_days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    start = date.fromisoformat(run.start_date)
    end = date.fromisoformat(run.end_date)
    tickers = list(dict.fromkeys(run.tickers))
    price_panel = await _load_price_panel(db, tickers, start, end)
    if price_panel.empty:
        return {"message": "No price history available for this backtest."}

    share_panel = _reconstruct_share_panel(trades, price_panel.index, price_panel.columns.tolist())
    market_value_panel = share_panel * price_panel
    gross_exposure_series = market_value_panel.abs().sum(axis=1)

    if not (gross_exposure_series > 1e-8).any():
        return {
            "message": "The backtest finished flat and did not retain a risk book to decompose."
        }

    snapshot_date = gross_exposure_series[gross_exposure_series > 1e-8].index[-1]
    snapshot_market_values = market_value_panel.loc[snapshot_date]
    snapshot_positions = snapshot_market_values[snapshot_market_values.abs() > 1e-8]

    if snapshot_positions.empty:
        return {"message": "No active positions were available at the selected risk snapshot."}

    equity_series = pd.Series(
        [point["value"] for point in run.equity_curve],
        index=pd.to_datetime([point["date"] for point in run.equity_curve]),
    ).sort_index()
    equity_value = float(equity_series.loc[:snapshot_date].iloc[-1])
    if abs(equity_value) <= 1e-8:
        return {"message": "Backtest equity was zero at the selected risk snapshot."}

    active_tickers = snapshot_positions.index.tolist()
    returns_window = (
        price_panel[active_tickers]
        .pct_change()
        .replace([np.inf, -np.inf], np.nan)
        .dropna(how="any")
        .loc[:snapshot_date]
        .tail(max(lookback_days, 20))
    )
    if len(returns_window) < 10:
        return {"message": "Not enough overlapping return history to estimate risk contributions."}

    weights = snapshot_positions / equity_value
    component_metrics = _compute_component_risk(
        returns_window=returns_window,
        weights=weights,
        equity_value=equity_value,
    )
    sectors = await get_ticker_sectors(active_tickers)
    snapshot_shares = share_panel.loc[snapshot_date]
    snapshot_prices = price_panel.loc[snapshot_date]

    positions = []
    for ticker in active_tickers:
        positions.append(
            {
                "ticker": ticker,
                "sector": sectors.get(ticker),
                "shares": int(round(snapshot_shares[ticker])),
                "price": round(float(snapshot_prices[ticker]), 4),
                "market_value": round(float(snapshot_positions[ticker]), 2),
                "weight_pct": round(float(weights[ticker] * 100), 2),
                "daily_volatility_pct": round(float(returns_window[ticker].std() * 100), 3),
                "beta_to_portfolio": round(float(component_metrics["betas"][ticker]), 3),
                "var_contribution": round(float(component_metrics["var_contributions"][ticker]), 2),
                "var_contribution_pct": round(
                    float(
                        component_metrics["var_contributions"][ticker]
                        / component_metrics["portfolio_var_dollar"]
                        * 100
                    ),
                    2,
                )
                if component_metrics["portfolio_var_dollar"] != 0
                else 0.0,
                "cvar_contribution": round(
                    float(component_metrics["cvar_contributions"][ticker]), 2
                ),
                "cvar_contribution_pct": round(
                    float(
                        component_metrics["cvar_contributions"][ticker]
                        / component_metrics["portfolio_cvar_dollar"]
                        * 100
                    ),
                    2,
                )
                if component_metrics["portfolio_cvar_dollar"] != 0
                else 0.0,
            }
        )
    positions.sort(key=lambda item: abs(item["var_contribution"]), reverse=True)

    scenarios = await _build_stress_scenarios(
        db=db,
        tickers=active_tickers,
        weights=weights,
        sectors=sectors,
        baseline_avg_correlation=component_metrics["average_pairwise_correlation"],
        equity_value=equity_value,
    )

    result = {
        "summary": {
            "snapshot_date": snapshot_date.date().isoformat(),
            "lookback_days": len(returns_window),
            "total_equity": round(equity_value, 2),
            "gross_exposure_pct": round(
                float((snapshot_positions.abs().sum() / abs(equity_value)) * 100), 2
            ),
            "net_exposure_pct": round(
                float((snapshot_positions.sum() / abs(equity_value)) * 100), 2
            ),
            "daily_var_95_pct": round(float(component_metrics["portfolio_var_pct"]), 3),
            "daily_var_95_dollar": round(float(component_metrics["portfolio_var_dollar"]), 2),
            "daily_cvar_95_pct": round(float(component_metrics["portfolio_cvar_pct"]), 3),
            "daily_cvar_95_dollar": round(float(component_metrics["portfolio_cvar_dollar"]), 2),
            "diversification_ratio": round(float(component_metrics["diversification_ratio"]), 3),
            "average_pairwise_correlation": round(
                float(component_metrics["average_pairwise_correlation"]),
                3,
            )
            if component_metrics["average_pairwise_correlation"] is not None
            else None,
        },
        "positions": positions,
        "scenarios": scenarios,
    }
    cache.put(cache_key, result, ttl=300)
    return result


def _reconstruct_share_panel(
    trades: list[TradeRecord | SimpleNamespace],
    date_index: pd.Index,
    tickers: list[str],
) -> pd.DataFrame:
    deltas = pd.DataFrame(0.0, index=date_index, columns=tickers)
    for trade in trades:
        if trade.ticker not in deltas.columns:
            deltas[trade.ticker] = 0.0

        if trade.position_direction == "LONG" and trade.side == "BUY":
            _apply_share_delta(deltas, trade.ticker, trade.entry_date, float(trade.shares))
        elif trade.position_direction == "LONG" and trade.side == "SELL" and trade.exit_date:
            _apply_share_delta(deltas, trade.ticker, trade.exit_date, -float(trade.shares))
        elif trade.position_direction == "SHORT" and trade.side == "SELL":
            _apply_share_delta(deltas, trade.ticker, trade.entry_date, -float(trade.shares))
        elif trade.position_direction == "SHORT" and trade.side == "BUY" and trade.exit_date:
            _apply_share_delta(deltas, trade.ticker, trade.exit_date, float(trade.shares))

    return deltas.sort_index().cumsum()


def _apply_share_delta(
    deltas: pd.DataFrame,
    ticker: str,
    trade_date: str,
    delta: float,
) -> None:
    effective_date = pd.Timestamp(trade_date)
    matching_index = deltas.index[deltas.index >= effective_date]
    if len(matching_index) == 0:
        return
    deltas.at[matching_index[0], ticker] += delta


def _compute_component_risk(
    *,
    returns_window: pd.DataFrame,
    weights: pd.Series,
    equity_value: float,
) -> dict[str, Any]:
    cov = returns_window.cov()
    weights = weights.reindex(cov.index).fillna(0.0)
    sigma_w = cov.to_numpy() @ weights.to_numpy()
    portfolio_vol = float(np.sqrt(weights.to_numpy() @ sigma_w))
    if portfolio_vol <= 1e-12:
        raise ValueError("Portfolio volatility was zero.")

    component_vol = weights.to_numpy() * sigma_w / portfolio_vol
    portfolio_var_pct = portfolio_vol * VAR_Z_95 * 100
    portfolio_var_dollar = portfolio_vol * VAR_Z_95 * equity_value

    portfolio_returns = returns_window.to_numpy() @ weights.to_numpy()
    cutoff = np.percentile(portfolio_returns, 5)
    tail_mask = portfolio_returns <= cutoff
    tail_returns = returns_window.loc[tail_mask]
    weighted_tail = tail_returns.mul(weights, axis=1)
    # Present CVaR as a positive loss magnitude while preserving hedging benefits
    # via negative component contributions when a position offsets the stress basket.
    portfolio_cvar_pct = (
        float(-weighted_tail.sum(axis=1).mean() * 100)
        if not weighted_tail.empty
        else float(-cutoff * 100)
    )
    portfolio_cvar_dollar = (
        float(-weighted_tail.sum(axis=1).mean() * equity_value)
        if not weighted_tail.empty
        else float(-cutoff * equity_value)
    )
    cvar_contributions = (
        -weighted_tail.mean(axis=0) * equity_value
        if not weighted_tail.empty
        else pd.Series(0.0, index=weights.index)
    )

    portfolio_return_var = float(np.var(portfolio_returns))
    betas = {}
    for ticker in weights.index:
        if portfolio_return_var <= 1e-12:
            betas[ticker] = 0.0
        else:
            betas[ticker] = (
                np.cov(returns_window[ticker], portfolio_returns)[0, 1] / portfolio_return_var
            )

    abs_weights = weights.abs().to_numpy()
    asset_vol = returns_window.std().to_numpy()
    diversification_ratio = (
        float((abs_weights @ asset_vol) / portfolio_vol) if portfolio_vol > 0 else 0.0
    )
    avg_pairwise_correlation, _, _ = _correlation_summary(returns_window)

    return {
        "var_contributions": pd.Series(
            component_vol * VAR_Z_95 * equity_value, index=weights.index
        ),
        "cvar_contributions": cvar_contributions.reindex(weights.index).fillna(0.0),
        "betas": pd.Series(betas),
        "portfolio_var_pct": portfolio_var_pct,
        "portfolio_var_dollar": portfolio_var_dollar,
        "portfolio_cvar_pct": portfolio_cvar_pct,
        "portfolio_cvar_dollar": portfolio_cvar_dollar,
        "diversification_ratio": diversification_ratio,
        "average_pairwise_correlation": avg_pairwise_correlation,
    }


async def _build_stress_scenarios(
    *,
    db: AsyncSession,
    tickers: list[str],
    weights: pd.Series,
    sectors: dict[str, str | None],
    baseline_avg_correlation: float | None,
    equity_value: float,
) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for scenario in STRESS_SCENARIOS:
        position_impacts: list[dict[str, Any]] = []
        scenario_returns: dict[str, float] = {}
        correlation_series: dict[str, pd.Series] = {}

        for ticker in tickers:
            proxy = SECTOR_PROXY_MAP.get(sectors.get(ticker) or "")
            scenario_return, source_ticker, returns_series = await _load_scenario_returns(
                db=db,
                ticker=ticker,
                proxy_ticker=proxy,
                start_date=scenario["start_date"],
                end_date=scenario["end_date"],
            )
            scenario_returns[ticker] = scenario_return
            if returns_series is not None:
                correlation_series[ticker] = returns_series

            pnl_impact = float(weights[ticker] * scenario_return * equity_value)
            position_impacts.append(
                {
                    "ticker": ticker,
                    "source_ticker": source_ticker,
                    "weight_pct": round(float(weights[ticker] * 100), 2),
                    "scenario_return_pct": round(float(scenario_return * 100), 2),
                    "pnl_impact": round(pnl_impact, 2),
                }
            )

        portfolio_return = sum(weights[ticker] * scenario_returns[ticker] for ticker in tickers)
        avg_corr, top_pair, top_pair_corr = (
            _correlation_summary(pd.DataFrame(correlation_series).dropna())
            if len(correlation_series) >= 2
            else (None, None, None)
        )
        position_impacts.sort(key=lambda item: item["pnl_impact"])
        scenarios.append(
            {
                "id": scenario["id"],
                "name": scenario["name"],
                "description": scenario["description"],
                "start_date": scenario["start_date"].isoformat(),
                "end_date": scenario["end_date"].isoformat(),
                "portfolio_return_pct": round(float(portfolio_return * 100), 2),
                "pnl_impact": round(float(portfolio_return * equity_value), 2),
                "average_pairwise_correlation": round(float(avg_corr), 3)
                if avg_corr is not None
                else None,
                "correlation_shift": round(float(avg_corr - baseline_avg_correlation), 3)
                if avg_corr is not None and baseline_avg_correlation is not None
                else None,
                "top_pair": top_pair,
                "top_pair_correlation": round(float(top_pair_corr), 3)
                if top_pair_corr is not None
                else None,
                "position_impacts": position_impacts[:5],
            }
        )

    return scenarios


async def _load_scenario_returns(
    *,
    db: AsyncSession,
    ticker: str,
    proxy_ticker: str | None,
    start_date: date,
    end_date: date,
) -> tuple[float, str, pd.Series | None]:
    for candidate in [ticker, proxy_ticker]:
        if not candidate:
            continue
        try:
            await ensure_data_loaded(db, candidate, start_date, end_date)
            df = await get_price_dataframe(db, candidate, start_date, end_date)
        except Exception:
            continue

        if df.empty or "adj_close" not in df:
            continue

        window_return = _compute_window_return(df["adj_close"])
        returns_series = df["adj_close"].pct_change().dropna()
        if window_return is not None:
            return window_return, candidate, returns_series

    return 0.0, proxy_ticker or ticker, None


def _compute_window_return(series: pd.Series) -> float | None:
    clean = series.dropna()
    if len(clean) < 2:
        return None
    start_value = float(clean.iloc[0])
    end_value = float(clean.iloc[-1])
    if abs(start_value) <= 1e-12:
        return None
    return (end_value / start_value) - 1


async def _load_price_panel(
    db: AsyncSession,
    tickers: list[str],
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    frames: list[pd.Series] = []
    for ticker in tickers:
        df = await get_price_dataframe(db, ticker, start_date, end_date)
        if df.empty or "adj_close" not in df:
            continue
        frames.append(df["adj_close"].rename(ticker))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).sort_index().ffill().dropna(how="all")


def _correlation_summary(
    returns_df: pd.DataFrame,
) -> tuple[float | None, str | None, float | None]:
    if returns_df.empty or returns_df.shape[1] < 2:
        return None, None, None
    corr = returns_df.corr()
    off_diag_values: list[float] = []
    best_pair: str | None = None
    best_value: float | None = None

    for a, b in combinations(corr.columns, 2):
        value = float(corr.loc[a, b])
        off_diag_values.append(value)
        if best_value is None or abs(value) > abs(best_value):
            best_value = value
            best_pair = f"{a}/{b}"

    if not off_diag_values:
        return None, best_pair, best_value
    return float(np.mean(off_diag_values)), best_pair, best_value
