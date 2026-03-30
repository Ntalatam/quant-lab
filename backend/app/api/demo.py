"""
POST /api/demo/seed  — Load demo data and run sample backtests
GET  /api/demo/status — Check if demo data has already been seeded
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session
from app.models.backtest import BacktestRun
from app.models.price_data import PriceData
from app.models.trade import TradeRecord
from app.schemas.backtest import BacktestConfig
from app.services.backtest_engine import run_backtest
from app.services.data_ingestion import ensure_data_loaded
from datetime import date

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_TICKERS = ["SPY", "AAPL", "MSFT", "GLD"]
DEMO_START = "2020-01-01"
DEMO_END = "2024-12-31"

DEMO_BACKTESTS = [
    BacktestConfig(
        strategy_id="sma_crossover",
        params={"short_window": 20, "long_window": 60, "position_weight": 0.95},
        tickers=["SPY", "AAPL", "MSFT"],
        benchmark="SPY",
        start_date=DEMO_START,
        end_date=DEMO_END,
        initial_capital=100_000,
        slippage_bps=5,
        commission_per_share=0.005,
        position_sizing="equal_weight",
        max_position_pct=40,
        rebalance_frequency="daily",
    ),
    BacktestConfig(
        strategy_id="momentum",
        params={"lookback_days": 90, "top_n": 2, "skip_days": 5, "position_weight": 0.9},
        tickers=["SPY", "AAPL", "MSFT", "GLD"],
        benchmark="SPY",
        start_date=DEMO_START,
        end_date=DEMO_END,
        initial_capital=100_000,
        slippage_bps=5,
        commission_per_share=0.005,
        position_sizing="equal_weight",
        max_position_pct=60,
        rebalance_frequency="monthly",
    ),
    BacktestConfig(
        strategy_id="mean_reversion",
        params={"lookback": 30, "num_std": 2.0, "position_weight": 0.8},
        tickers=["AAPL"],
        benchmark="SPY",
        start_date=DEMO_START,
        end_date=DEMO_END,
        initial_capital=100_000,
        slippage_bps=5,
        commission_per_share=0.005,
        position_sizing="equal_weight",
        max_position_pct=80,
        rebalance_frequency="daily",
    ),
]


@router.get("/status")
async def demo_status(db: AsyncSession = Depends(get_db)):
    """Check if demo data is already loaded."""
    ticker_count = await db.scalar(
        select(func.count()).select_from(
            select(PriceData.ticker)
            .where(PriceData.ticker.in_(DEMO_TICKERS))
            .distinct()
            .subquery()
        )
    )
    run_count = await db.scalar(
        select(func.count()).select_from(BacktestRun)
    )
    return {
        "tickers_loaded": int(ticker_count or 0),
        "total_tickers": len(DEMO_TICKERS),
        "backtests_exist": int(run_count or 0) > 0,
        "seeded": int(ticker_count or 0) >= 2,
    }


@router.post("/seed")
async def seed_demo(db: AsyncSession = Depends(get_db)):
    """
    Load demo tickers and run 3 sample backtests.
    Returns immediately with IDs of newly created backtests.
    """
    start = date.fromisoformat(DEMO_START)
    end = date.fromisoformat(DEMO_END)

    # Load all demo tickers
    loaded_tickers = []
    failed_tickers = []
    for ticker in DEMO_TICKERS:
        ok = await ensure_data_loaded(db, ticker, start, end)
        if ok:
            loaded_tickers.append(ticker)
        else:
            failed_tickers.append(ticker)

    # Run demo backtests
    backtest_ids = []
    errors = []

    for config in DEMO_BACKTESTS:
        # Skip if required tickers failed to load
        required = [t for t in config.tickers if t not in loaded_tickers]
        if len(required) == len(config.tickers):
            errors.append(f"Skipped {config.strategy_id}: no tickers available")
            continue
        # Use only loaded tickers
        actual_tickers = [t for t in config.tickers if t in loaded_tickers]
        if not actual_tickers:
            continue
        run_config = config.model_copy(update={"tickers": actual_tickers})
        try:
            async with async_session() as db2:
                result = await run_backtest(db2, run_config)
                run = BacktestRun(
                    id=result["id"],
                    strategy_id=run_config.strategy_id,
                    strategy_params=run_config.params,
                    tickers=run_config.tickers,
                    benchmark=run_config.benchmark,
                    start_date=run_config.start_date,
                    end_date=run_config.end_date,
                    initial_capital=run_config.initial_capital,
                    slippage_bps=run_config.slippage_bps,
                    commission_per_share=run_config.commission_per_share,
                    position_sizing=run_config.position_sizing,
                    max_position_pct=run_config.max_position_pct,
                    rebalance_frequency=run_config.rebalance_frequency,
                    equity_curve=result["equity_curve"],
                    clean_equity_curve=result.get("clean_equity_curve", []),
                    benchmark_curve=result["benchmark_curve"],
                    drawdown_series=result["drawdown_series"],
                    rolling_sharpe=result["rolling_sharpe"],
                    rolling_volatility=result["rolling_volatility"],
                    monthly_returns=result["monthly_returns"],
                    metrics=result["metrics"],
                    benchmark_metrics=result["benchmark_metrics"],
                )
                db2.add(run)
                for trade in result["trades"]:
                    tr = TradeRecord(
                        id=trade["id"],
                        backtest_run_id=result["id"],
                        ticker=trade["ticker"],
                        side=trade["side"],
                        entry_date=trade["entry_date"],
                        entry_price=trade["entry_price"],
                        exit_date=trade["exit_date"],
                        exit_price=trade["exit_price"],
                        shares=trade["shares"],
                        pnl=trade["pnl"],
                        pnl_pct=trade["pnl_pct"],
                        commission=trade["commission"],
                        slippage=trade["slippage"],
                    )
                    db2.add(tr)
                await db2.commit()
                backtest_ids.append(result["id"])
        except Exception as e:
            errors.append(f"{config.strategy_id}: {str(e)}")

    return {
        "status": "ok" if backtest_ids else "partial",
        "tickers_loaded": loaded_tickers,
        "tickers_failed": failed_tickers,
        "backtests_created": backtest_ids,
        "errors": errors,
    }
