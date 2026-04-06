"""
Walk-forward analysis.

Divides the historical period into N rolling windows. For each window the
strategy runs on the out-of-sample (OOS) slice using fixed parameters.
Stitching the OOS slices gives a continuous OOS equity curve — this is
what real-world deployment of the strategy would look like.

The OOS curve is compared against the full in-sample (IS) curve to reveal
whether the strategy is robust or if its paper performance depends on having
seen the whole dataset at once.
"""

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.backtest import BacktestConfig
from app.services.analytics import compute_all_metrics
from app.services.backtest_engine import run_backtest


def _split_date_range(start: date, end: date, n_folds: int, train_pct: float):
    """
    Yields (is_start, is_end, oos_start, oos_end) tuples for rolling windows.

    Each fold covers total_days / n_folds days, split train_pct in-sample /
    (1-train_pct) out-of-sample.
    """
    total_days = (end - start).days
    fold_days = total_days // n_folds
    if fold_days < 30:
        raise ValueError("Date range too short for the requested number of folds.")

    train_days = int(fold_days * train_pct)
    oos_days = fold_days - train_days

    if train_days < 20 or oos_days < 10:
        raise ValueError(
            "train_pct produces windows that are too short. Use fewer folds or a wider date range."
        )

    for i in range(n_folds):
        window_start = start + timedelta(days=i * fold_days)
        is_start = window_start
        is_end = window_start + timedelta(days=train_days - 1)
        oos_start = is_end + timedelta(days=1)
        oos_end = window_start + timedelta(days=fold_days - 1)
        if oos_end > end:
            oos_end = end
        if oos_start >= oos_end:
            continue
        yield is_start, is_end, oos_start, oos_end


async def run_walk_forward(
    db: AsyncSession,
    config: BacktestConfig,
    n_folds: int = 5,
    train_pct: float = 0.7,
    *,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """
    Run walk-forward analysis and return fold statistics + combined OOS equity curve.
    """
    start = date.fromisoformat(config.start_date)
    end = date.fromisoformat(config.end_date)

    splits = list(_split_date_range(start, end, n_folds, train_pct))
    if not splits:
        raise ValueError("Could not create valid WFA splits from this date range.")

    folds = []
    oos_equity_segments = []  # list of (dates, values) per OOS fold
    oos_capital = config.initial_capital  # carry forward OOS equity across folds

    for fold_idx, (is_start, is_end, oos_start, oos_end) in enumerate(splits):
        # --- In-sample run (for IS metrics only) ---
        is_config = config.model_copy(
            update={
                "start_date": is_start.isoformat(),
                "end_date": is_end.isoformat(),
                "initial_capital": config.initial_capital,
            }
        )
        try:
            is_result = await run_backtest(db, is_config, workspace_id=workspace_id)
            is_sharpe = is_result["metrics"].get("sharpe_ratio", 0)
            is_return = is_result["metrics"].get("total_return_pct", 0)
        except Exception:
            is_sharpe = None
            is_return = None

        # --- Out-of-sample run (uses equity from prior OOS fold as capital) ---
        oos_config = config.model_copy(
            update={
                "start_date": oos_start.isoformat(),
                "end_date": oos_end.isoformat(),
                "initial_capital": oos_capital,
            }
        )
        try:
            oos_result = await run_backtest(db, oos_config, workspace_id=workspace_id)
            oos_sharpe = oos_result["metrics"].get("sharpe_ratio", 0)
            oos_return = oos_result["metrics"].get("total_return_pct", 0)
            oos_max_dd = oos_result["metrics"].get("max_drawdown_pct", 0)
            oos_curve = oos_result["equity_curve"]
            fold_ok = True

            # Carry equity forward
            if oos_curve:
                oos_capital = oos_curve[-1]["value"]
            oos_equity_segments.extend(oos_curve)
        except Exception:
            oos_sharpe = None
            oos_return = None
            oos_max_dd = None
            fold_ok = False

        folds.append(
            {
                "fold": fold_idx + 1,
                "is_start": is_start.isoformat(),
                "is_end": is_end.isoformat(),
                "oos_start": oos_start.isoformat(),
                "oos_end": oos_end.isoformat(),
                "is_sharpe": round(is_sharpe, 3) if is_sharpe is not None else None,
                "is_return": round(is_return, 2) if is_return is not None else None,
                "oos_sharpe": round(oos_sharpe, 3) if oos_sharpe is not None else None,
                "oos_return": round(oos_return, 2) if oos_return is not None else None,
                "oos_max_dd": round(oos_max_dd, 2) if oos_max_dd is not None else None,
                "ok": fold_ok,
            }
        )

    # --- Combined OOS curve metrics ---
    oos_metrics: dict = {}
    if oos_equity_segments:
        oos_series = pd.Series(
            [p["value"] for p in oos_equity_segments],
            index=pd.to_datetime([p["date"] for p in oos_equity_segments]),
        )
        bench_series = pd.Series(dtype=float)
        oos_metrics = compute_all_metrics(oos_series, bench_series, config.initial_capital)

    # --- IS/OOS Sharpe efficiency ---
    valid_folds = [f for f in folds if f["is_sharpe"] is not None and f["oos_sharpe"] is not None]
    sharpe_efficiency = None
    if valid_folds:
        avg_is = np.mean([f["is_sharpe"] for f in valid_folds])
        avg_oos = np.mean([f["oos_sharpe"] for f in valid_folds])
        if avg_is != 0:
            sharpe_efficiency = round(avg_oos / avg_is, 3)

    return {
        "n_folds": n_folds,
        "train_pct": train_pct,
        "folds": folds,
        "oos_equity_curve": oos_equity_segments,
        "oos_metrics": oos_metrics,
        "sharpe_efficiency": sharpe_efficiency,  # OOS Sharpe / IS Sharpe — ideally close to 1.0
    }
