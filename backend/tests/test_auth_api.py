from __future__ import annotations

import asyncio
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main as app_main
from app.database import Base, get_db
from app.schemas.backtest import BacktestConfig
from app.services.backtest_runs import persist_backtest_result


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
        "id": "bt_auth_001",
        "equity_curve": [{"date": "2024-01-02", "value": 100000.0}],
        "clean_equity_curve": [{"date": "2024-01-02", "value": 100010.0}],
        "benchmark_curve": [{"date": "2024-01-02", "value": 100000.0}],
        "drawdown_series": [{"date": "2024-01-02", "value": 0.0}],
        "rolling_sharpe": [{"date": "2024-01-31", "value": 1.2}],
        "rolling_volatility": [{"date": "2024-01-31", "value": 12.5}],
        "monthly_returns": [{"year": 2024, "month": 1, "return_pct": 1.3}],
        "metrics": {"total_return_pct": 1.3, "sharpe_ratio": 1.2},
        "benchmark_metrics": {"total_return_pct": 1.0, "sharpe_ratio": 0.9},
        "trades": [],
    }


@contextmanager
def _build_client(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "auth-api.db"
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

    try:
        with TestClient(app) as client:
            yield client, session_factory
    finally:
        asyncio.run(_dispose())


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_auth_register_refresh_logout_and_login(monkeypatch, tmp_path):
    with _build_client(monkeypatch, tmp_path) as (client, _session_factory):
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "alice@example.com",
                "password": "supersecret1",
                "display_name": "Alice",
            },
        )

        assert register_response.status_code == 200
        payload = register_response.json()
        access_token = payload["access_token"]
        assert payload["workspace"]["is_personal"] is True
        assert "quantlab_refresh_token" in register_response.headers["set-cookie"]

        me_response = client.get("/api/auth/me", headers=_auth_headers(access_token))
        assert me_response.status_code == 200
        assert me_response.json()["user"]["email"] == "alice@example.com"

        refresh_response = client.post("/api/auth/refresh")
        assert refresh_response.status_code == 200
        assert refresh_response.json()["user"]["email"] == "alice@example.com"

        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 200

        failed_refresh = client.post("/api/auth/refresh")
        assert failed_refresh.status_code == 401

        login_response = client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "supersecret1"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["workspace"]["name"] == "Alice Personal"


def test_workspace_scoping_hides_backtests_from_other_users(monkeypatch, tmp_path):
    config = _build_config()
    result = _build_result()

    with _build_client(monkeypatch, tmp_path) as (client, session_factory):
        alice = client.post(
            "/api/auth/register",
            json={"email": "alice@example.com", "password": "supersecret1"},
        )
        bob = client.post(
            "/api/auth/register",
            json={"email": "bob@example.com", "password": "supersecret2"},
        )

        alice_token = alice.json()["access_token"]
        bob_token = bob.json()["access_token"]
        alice_user_id = alice.json()["user"]["id"]
        alice_workspace_id = alice.json()["workspace"]["id"]

        async def _persist():
            async with session_factory() as session:
                await persist_backtest_result(
                    session,
                    config,
                    result,
                    workspace_id=alice_workspace_id,
                    created_by_user_id=alice_user_id,
                )

        asyncio.run(_persist())

        alice_list = client.get("/api/backtest/list", headers=_auth_headers(alice_token))
        bob_list = client.get("/api/backtest/list", headers=_auth_headers(bob_token))
        bob_detail = client.get(
            f"/api/backtest/{result['id']}",
            headers=_auth_headers(bob_token),
        )

        assert alice_list.status_code == 200
        assert alice_list.json()["total"] == 1
        assert bob_list.status_code == 200
        assert bob_list.json()["total"] == 0
        assert bob_detail.status_code == 404
