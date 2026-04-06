from __future__ import annotations

import asyncio
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main as app_main
from app.config import settings
from app.database import Base, get_db


async def _noop():
    return None


@contextmanager
def _build_client(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "paper-api.db"
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
    monkeypatch.setattr(app_main, "engine", engine)
    monkeypatch.setattr(app_main, "async_session", session_factory)
    monkeypatch.setattr(settings, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(settings, "ALPACA_SECRET_KEY", "test-secret")

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
            yield client
    finally:
        asyncio.run(_dispose())


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "display_name": email.split("@", 1)[0].title(),
        },
    )
    assert response.status_code == 200
    return response.json()


def test_paper_session_create_detail_and_workspace_scoping(monkeypatch, tmp_path):
    with _build_client(monkeypatch, tmp_path) as client:
        alice = _register(client, "alice@example.com")
        bob = _register(client, "bob@example.com")

        alice_headers = _auth_headers(alice["access_token"])
        bob_headers = _auth_headers(bob["access_token"])

        create_response = client.post(
            "/api/paper/sessions",
            headers=alice_headers,
            json={
                "name": "Momentum Broker Session",
                "execution_mode": "broker_paper",
                "broker_adapter": "alpaca",
                "strategy_id": "sma_crossover",
                "params": {"short_window": 20, "long_window": 60},
                "tickers": ["AAPL", "MSFT"],
                "benchmark": "SPY",
                "initial_capital": 100000,
                "slippage_bps": 5,
                "commission_per_share": 0.005,
                "market_impact_model": "almgren_chriss",
                "max_volume_participation_pct": 5,
                "portfolio_construction_model": "equal_weight",
                "portfolio_lookback_days": 63,
                "max_position_pct": 25,
                "max_gross_exposure_pct": 150,
                "turnover_limit_pct": 100,
                "max_sector_exposure_pct": 100,
                "allow_short_selling": False,
                "max_short_position_pct": 25,
                "short_margin_requirement_pct": 50,
                "short_borrow_rate_bps": 200,
                "short_locate_fee_bps": 10,
                "short_squeeze_threshold_pct": 15,
                "bar_interval": "1m",
                "polling_interval_seconds": 60,
                "start_immediately": False,
            },
        )

        assert create_response.status_code == 200
        created = create_response.json()
        session_id = created["id"]
        assert created["execution_mode"] == "broker_paper"
        assert created["broker_adapter"] == "alpaca"
        assert created["broker_account_label"] == "Alpaca paper"
        assert created["open_order_count"] == 0
        assert created["recent_orders"] == []
        assert created["recent_executions"] == []

        alice_list = client.get("/api/paper/sessions", headers=alice_headers)
        bob_list = client.get("/api/paper/sessions", headers=bob_headers)
        bob_detail = client.get(f"/api/paper/sessions/{session_id}", headers=bob_headers)

        assert alice_list.status_code == 200
        assert len(alice_list.json()) == 1
        assert alice_list.json()[0]["execution_mode"] == "broker_paper"
        assert bob_list.status_code == 200
        assert bob_list.json() == []
        assert bob_detail.status_code == 404


def test_paper_session_defaults_to_simulated_paper(monkeypatch, tmp_path):
    with _build_client(monkeypatch, tmp_path) as client:
        alice = _register(client, "alice@example.com")
        alice_headers = _auth_headers(alice["access_token"])

        create_response = client.post(
            "/api/paper/sessions",
            headers=alice_headers,
            json={
                "name": "SMA Session",
                "strategy_id": "sma_crossover",
                "params": {"short_window": 20, "long_window": 60},
                "tickers": ["AAPL"],
                "benchmark": "SPY",
                "initial_capital": 100000,
                "slippage_bps": 5,
                "commission_per_share": 0.005,
                "market_impact_model": "almgren_chriss",
                "max_volume_participation_pct": 5,
                "portfolio_construction_model": "equal_weight",
                "portfolio_lookback_days": 63,
                "max_position_pct": 25,
                "max_gross_exposure_pct": 150,
                "turnover_limit_pct": 100,
                "max_sector_exposure_pct": 100,
                "allow_short_selling": False,
                "max_short_position_pct": 25,
                "short_margin_requirement_pct": 50,
                "short_borrow_rate_bps": 200,
                "short_locate_fee_bps": 10,
                "short_squeeze_threshold_pct": 15,
                "bar_interval": "1m",
                "polling_interval_seconds": 60,
                "start_immediately": False,
            },
        )

        assert create_response.status_code == 200
        created = create_response.json()
        assert created["execution_mode"] == "simulated_paper"
        assert created["broker_adapter"] == "paper"
        assert created["broker_account_label"] == "Local simulator"
