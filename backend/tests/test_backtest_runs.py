from __future__ import annotations

import pytest

from app.schemas.backtest import BacktestConfig
from app.services.backtest_runs import (
    load_backtest_detail,
    persist_backtest_result,
    serialize_backtest_run,
)


def _build_config() -> BacktestConfig:
    return BacktestConfig(
        strategy_id="sma_crossover",
        params={"short_window": 20, "long_window": 60},
        tickers=["MSFT", "AAPL"],
        benchmark="SPY",
        start_date="2024-01-01",
        end_date="2024-03-01",
        initial_capital=100_000,
        slippage_bps=5,
        commission_per_share=0.005,
        market_impact_model="almgren_chriss",
        max_volume_participation_pct=5,
        position_sizing="equal_weight",
        portfolio_construction_model="risk_parity",
        portfolio_lookback_days=63,
        max_position_pct=25,
        max_gross_exposure_pct=150,
        turnover_limit_pct=100,
        max_sector_exposure_pct=100,
        allow_short_selling=False,
        max_short_position_pct=25,
        short_margin_requirement_pct=50,
        short_borrow_rate_bps=200,
        short_locate_fee_bps=10,
        short_squeeze_threshold_pct=15,
        rebalance_frequency="daily",
    )


def _build_result() -> dict:
    return {
        "id": "bt_test_001",
        "equity_curve": [{"date": "2024-01-02", "value": 100000.0}],
        "clean_equity_curve": [{"date": "2024-01-02", "value": 100010.0}],
        "benchmark_curve": [{"date": "2024-01-02", "value": 100000.0}],
        "drawdown_series": [{"date": "2024-01-02", "value": 0.0}],
        "rolling_sharpe": [{"date": "2024-01-31", "value": 1.2}],
        "rolling_volatility": [{"date": "2024-01-31", "value": 12.5}],
        "monthly_returns": [{"year": 2024, "month": 1, "return_pct": 1.3}],
        "metrics": {"total_return_pct": 1.3, "sharpe_ratio": 1.2},
        "benchmark_metrics": {"total_return_pct": 1.0, "sharpe_ratio": 0.9},
        "trades": [
            {
                "id": "trade_z",
                "ticker": "MSFT",
                "side": "BUY",
                "position_direction": "LONG",
                "entry_date": "2024-01-03",
                "entry_price": 380.0,
                "exit_date": "2024-01-10",
                "exit_price": 390.0,
                "shares": 10,
                "requested_shares": 10,
                "unfilled_shares": 0,
                "pnl": 100.0,
                "pnl_pct": 2.63,
                "commission": 0.05,
                "slippage": 1.0,
                "spread_cost": 0.5,
                "market_impact_cost": 0.2,
                "timing_cost": 0.1,
                "opportunity_cost": 0.0,
                "participation_rate_pct": 1.5,
                "implementation_shortfall": 1.8,
                "borrow_cost": 0.0,
                "locate_fee": 0.0,
                "risk_event": None,
            },
            {
                "id": "trade_a",
                "ticker": "AAPL",
                "side": "BUY",
                "position_direction": "LONG",
                "entry_date": "2024-01-02",
                "entry_price": 190.0,
                "exit_date": "2024-01-08",
                "exit_price": 195.0,
                "shares": 12,
                "requested_shares": 12,
                "unfilled_shares": 0,
                "pnl": 60.0,
                "pnl_pct": 2.63,
                "commission": 0.06,
                "slippage": 0.8,
                "spread_cost": 0.4,
                "market_impact_cost": 0.15,
                "timing_cost": 0.05,
                "opportunity_cost": 0.0,
                "participation_rate_pct": 1.1,
                "implementation_shortfall": 1.4,
                "borrow_cost": 0.0,
                "locate_fee": 0.0,
                "risk_event": None,
            },
        ],
    }


@pytest.mark.asyncio
async def test_persist_and_load_backtest_detail(db):
    config = _build_config()
    result = _build_result()

    await persist_backtest_result(db, config, result)
    detail = await load_backtest_detail(db, result["id"])

    assert detail is not None
    run, trades = detail
    assert run.id == result["id"]
    assert [trade.ticker for trade in trades] == ["AAPL", "MSFT"]
    assert trades[0].entry_date == "2024-01-02"
    assert trades[1].entry_date == "2024-01-03"


@pytest.mark.asyncio
async def test_serialize_backtest_run_preserves_config_and_trade_fields(db):
    config = _build_config()
    result = _build_result()

    run, trades = await persist_backtest_result(db, config, result)
    payload = serialize_backtest_run(run, trades)

    assert payload["config"]["strategy_id"] == "sma_crossover"
    assert payload["config"]["portfolio_construction_model"] == "risk_parity"
    assert payload["config"]["market_impact_model"] == "almgren_chriss"
    assert payload["metrics"]["sharpe_ratio"] == 1.2
    assert payload["trades"][0]["ticker"] == "AAPL"
    assert payload["trades"][0]["implementation_shortfall"] == 1.4
    assert payload["trades"][1]["ticker"] == "MSFT"
