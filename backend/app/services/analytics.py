"""
Analytics engine.

Computes comprehensive performance and risk metrics from an equity curve.
All metrics follow standard quantitative finance definitions:
- Simple returns (not log) for interpretability
- 252 trading days/year annualization
- Risk-free rate = 0 for Sharpe/Sortino
- VaR/CVaR via historical simulation
"""

import numpy as np
import pandas as pd
from scipy import stats


def compute_all_metrics(
    equity: pd.Series,
    benchmark: pd.Series,
    initial_capital: float,
) -> dict:
    """Compute all performance and risk metrics."""
    if len(equity) < 2:
        return _empty_metrics()

    returns = equity.pct_change().dropna()
    bench_returns = benchmark.pct_change().dropna()

    aligned = pd.DataFrame(
        {"strategy": returns, "benchmark": bench_returns}
    ).dropna()
    strat_ret = aligned["strategy"]
    bench_ret = aligned["benchmark"]

    n_days = len(returns)
    n_years = n_days / 252

    # Returns
    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / max(n_years, 0.01)) - 1
    annualized_return = returns.mean() * 252

    # Risk
    ann_vol = returns.std() * np.sqrt(252)
    downside_returns = returns[returns < 0]
    downside_vol = (
        downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
    )

    # Drawdown
    rolling_max = equity.expanding().max()
    drawdown = (equity - rolling_max) / rolling_max
    max_dd = drawdown.min()
    dd_duration = _max_drawdown_duration(drawdown)
    current_dd = float(drawdown.iloc[-1])

    # Risk-adjusted
    sharpe = (
        (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
    )
    sortino = (
        (returns.mean() / downside_vol) * np.sqrt(252) if downside_vol > 0 else 0
    )
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0

    # Information ratio
    excess = strat_ret - bench_ret
    tracking_error = excess.std() * np.sqrt(252)
    info_ratio = (
        (excess.mean() * 252) / tracking_error if tracking_error > 0 else 0
    )

    # Tail risk
    var_95 = np.percentile(returns, 5) if len(returns) > 20 else 0
    cvar_95 = (
        returns[returns <= var_95].mean()
        if len(returns[returns <= var_95]) > 0
        else var_95
    )
    skew = float(stats.skew(returns)) if len(returns) > 3 else 0
    kurt = float(stats.kurtosis(returns)) if len(returns) > 3 else 0

    # Daily win/loss stats
    winning_days = returns[returns > 0]
    losing_days = returns[returns < 0]
    win_rate = len(winning_days) / len(returns) * 100 if len(returns) > 0 else 0
    avg_win = winning_days.mean() * 100 if len(winning_days) > 0 else 0
    avg_loss = losing_days.mean() * 100 if len(losing_days) > 0 else 0
    profit_factor = (
        (winning_days.sum() / abs(losing_days.sum()))
        if abs(losing_days.sum()) > 0
        else float("inf")
    )

    # Benchmark relative
    if len(aligned) > 10:
        beta, alpha_daily, _, _, _ = stats.linregress(bench_ret, strat_ret)
        alpha = alpha_daily * 252
        correlation = strat_ret.corr(bench_ret)
    else:
        beta = 0
        alpha = 0
        correlation = 0

    return {
        "total_return_pct": round(total_return * 100, 2),
        "annualized_return_pct": round(annualized_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "annualized_volatility_pct": round(ann_vol * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "max_drawdown_duration_days": dd_duration,
        "current_drawdown_pct": round(current_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "calmar_ratio": round(calmar, 3),
        "information_ratio": round(info_ratio, 3),
        "var_95_pct": round(var_95 * 100, 3),
        "cvar_95_pct": round(cvar_95 * 100, 3),
        "skewness": round(skew, 3),
        "kurtosis": round(kurt, 3),
        "total_trades": 0,
        "win_rate_pct": round(win_rate, 2),
        "avg_win_pct": round(avg_win, 3),
        "avg_loss_pct": round(avg_loss, 3),
        "profit_factor": round(min(profit_factor, 9999), 3),
        "avg_holding_period_days": 0,
        "best_trade_pct": round(returns.max() * 100, 3) if len(returns) > 0 else 0,
        "worst_trade_pct": round(returns.min() * 100, 3) if len(returns) > 0 else 0,
        "avg_exposure_pct": 0,
        "max_exposure_pct": 0,
        "alpha": round(alpha * 100, 3),
        "beta": round(beta, 3),
        "correlation": round(correlation, 3),
        "tracking_error_pct": round(tracking_error * 100, 2),
    }


def compute_trade_statistics(trade_log: list[dict]) -> dict:
    """Compute trade-level statistics from the trade log."""
    sells = [t for t in trade_log if t.get("side") == "SELL" and t.get("pnl") is not None]
    if not sells:
        return {"total_trades": 0, "win_rate_pct": 0, "avg_holding_period_days": 0}

    wins = [t for t in sells if t["pnl"] > 0]
    losses = [t for t in sells if t["pnl"] <= 0]

    holding_periods = []
    for t in sells:
        if t.get("entry_date") and t.get("exit_date"):
            try:
                entry = pd.Timestamp(t["entry_date"])
                exit_ = pd.Timestamp(t["exit_date"])
                holding_periods.append((exit_ - entry).days)
            except Exception:
                pass

    return {
        "total_trades": len(sells),
        "win_rate_pct": round(len(wins) / len(sells) * 100, 2),
        "avg_win_pct": round(
            np.mean([t["pnl_pct"] for t in wins]), 3
        ) if wins else 0,
        "avg_loss_pct": round(
            np.mean([t["pnl_pct"] for t in losses]), 3
        ) if losses else 0,
        "best_trade_pct": round(max(t["pnl_pct"] for t in sells), 3),
        "worst_trade_pct": round(min(t["pnl_pct"] for t in sells), 3),
        "profit_factor": round(
            sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses)), 3
        ) if losses and sum(t["pnl"] for t in losses) != 0 else 9999,
        "avg_holding_period_days": round(np.mean(holding_periods), 1) if holding_periods else 0,
    }


def compute_monthly_returns(equity: pd.Series) -> list[dict]:
    """Compute monthly return grid for heatmap display."""
    monthly = equity.resample("ME").last().pct_change().dropna()
    result = []
    for idx, val in monthly.items():
        result.append(
            {
                "year": idx.year,
                "month": idx.month,
                "return_pct": round(val * 100, 2),
            }
        )
    return result


def compute_monte_carlo(
    returns: pd.Series,
    n_simulations: int = 1000,
    n_days: int = 252,
    initial_value: float = 100_000,
) -> dict:
    """
    Monte Carlo simulation by sampling from historical return distribution.
    Returns percentile bands for fan chart visualization.
    """
    mu = returns.mean()
    sigma = returns.std()

    rng = np.random.default_rng(42)
    simulations = np.zeros((n_simulations, n_days))
    simulations[:, 0] = initial_value

    for i in range(1, n_days):
        random_returns = rng.normal(mu, sigma, n_simulations)
        simulations[:, i] = simulations[:, i - 1] * (1 + random_returns)

    percentiles = {}
    for p in [5, 25, 50, 75, 95]:
        percentiles[f"p{p}"] = np.percentile(simulations, p, axis=0).tolist()

    return {
        "percentiles": percentiles,
        "n_simulations": n_simulations,
        "n_days": n_days,
        "median_final_value": float(np.median(simulations[:, -1])),
        "prob_loss": float(np.mean(simulations[:, -1] < initial_value)),
    }


def _max_drawdown_duration(drawdown: pd.Series) -> int:
    """Calculate the longest drawdown period in trading days."""
    in_dd = drawdown < 0
    if not in_dd.any():
        return 0

    groups = (~in_dd).cumsum()
    dd_groups = in_dd.groupby(groups)
    max_duration = dd_groups.sum().max()
    return int(max_duration)


def _empty_metrics() -> dict:
    """Return zeroed metrics dict for edge cases."""
    return {
        k: 0
        for k in [
            "total_return_pct", "annualized_return_pct", "cagr_pct",
            "annualized_volatility_pct", "max_drawdown_pct",
            "max_drawdown_duration_days", "current_drawdown_pct",
            "sharpe_ratio", "sortino_ratio", "calmar_ratio",
            "information_ratio", "var_95_pct", "cvar_95_pct",
            "skewness", "kurtosis", "total_trades", "win_rate_pct",
            "avg_win_pct", "avg_loss_pct", "profit_factor",
            "avg_holding_period_days", "best_trade_pct", "worst_trade_pct",
            "avg_exposure_pct", "max_exposure_pct", "alpha", "beta",
            "correlation", "tracking_error_pct",
        ]
    }
