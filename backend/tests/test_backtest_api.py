from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main as app_main
from app.api import backtest as backtest_api
from app.database import Base, get_db
from app.schemas.backtest import BacktestConfig
from app.services.backtest_runs import load_backtest_detail
from tests.auth_helpers import TEST_USER, TEST_WORKSPACE, install_auth_overrides


class _FakePaperManager:
    def __init__(self, *_args, **_kwargs):
        pass

    async def resume_active_sessions(self):
        return None

    async def shutdown(self):
        return None

    def health_summary(self):
        return {"runtime_sessions": 0, "subscriber_channels": 0}


async def _noop():
    return None


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


def _build_result() -> dict[str, Any]:
    return {
        "id": "bt_api_001",
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


@contextmanager
def _build_client(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "backtest-api.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _prepare():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _dispose():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_prepare())

    monkeypatch.setattr(app_main, "init_db", _noop)
    monkeypatch.setattr(app_main, "PaperTradingManager", _FakePaperManager)
    monkeypatch.setattr(app_main, "engine", engine)

    async def fake_authenticate_websocket(_websocket, _db):
        return TEST_USER, TEST_WORKSPACE

    monkeypatch.setattr(backtest_api, "authenticate_websocket", fake_authenticate_websocket)

    import app.database as app_database

    monkeypatch.setattr(app_database, "async_session", session_factory)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = app_main.create_app()
    app.dependency_overrides[get_db] = override_get_db
    install_auth_overrides(app)

    try:
        with TestClient(app) as client:
            yield client, session_factory
    finally:
        asyncio.run(_dispose())


async def _load_detail(session_factory, backtest_id: str):
    async with session_factory() as session:
        return await load_backtest_detail(session, backtest_id)


def test_execute_backtest_route_persists_and_returns_sorted_trades(monkeypatch, tmp_path):
    config = _build_config()
    result = _build_result()

    async def fake_run_backtest(_db, _config, on_progress=None, workspace_id=None):
        assert workspace_id == TEST_WORKSPACE.id
        if on_progress is not None:
            await on_progress(1, 1, "2024-01-31", 100_500)
        return result

    monkeypatch.setattr(backtest_api, "run_backtest", fake_run_backtest)

    with _build_client(monkeypatch, tmp_path) as (client, session_factory):
        response = client.post("/api/backtest/run", json=config.model_dump())

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == result["id"]
        assert [trade["ticker"] for trade in payload["trades"]] == ["AAPL", "MSFT"]

        detail = asyncio.run(_load_detail(session_factory, result["id"]))
        assert detail is not None
        run, trades = detail
        assert run.strategy_id == config.strategy_id
        assert [trade.ticker for trade in trades] == ["AAPL", "MSFT"]


def test_backtest_websocket_persists_result_and_streams_progress(monkeypatch, tmp_path):
    config = _build_config()
    result = _build_result()

    async def fake_run_backtest(_db, _config, on_progress=None, workspace_id=None):
        assert workspace_id == TEST_WORKSPACE.id
        if on_progress is not None:
            await on_progress(25, 100, "2024-02-01", 103_250)
        return result

    monkeypatch.setattr(backtest_api, "run_backtest", fake_run_backtest)

    with _build_client(monkeypatch, tmp_path) as (client, session_factory):
        with client.websocket_connect("/api/backtest/ws") as websocket:
            websocket.send_text(json.dumps(config.model_dump()))

            progress_message = websocket.receive_json()
            complete_message = websocket.receive_json()

        assert progress_message["type"] == "progress"
        assert progress_message["pct"] == 0.25
        assert complete_message == {"type": "complete", "id": result["id"]}

        detail = asyncio.run(_load_detail(session_factory, result["id"]))
        assert detail is not None
        _, trades = detail
        assert len(trades) == 2


def test_backtest_websocket_rejects_invalid_json(monkeypatch, tmp_path):
    with (
        _build_client(monkeypatch, tmp_path) as (client, _session_factory),
        client.websocket_connect("/api/backtest/ws") as websocket,
    ):
        websocket.send_text("{")
        message = websocket.receive_json()

    assert message == {"type": "error", "message": "Invalid JSON payload"}


def test_backtest_websocket_rejects_invalid_config(monkeypatch, tmp_path):
    with (
        _build_client(monkeypatch, tmp_path) as (client, _session_factory),
        client.websocket_connect("/api/backtest/ws") as websocket,
    ):
        websocket.send_text(json.dumps({"strategy_id": "sma_crossover"}))
        message = websocket.receive_json()

    assert message == {"type": "error", "message": "Invalid backtest config"}
