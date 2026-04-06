from __future__ import annotations

import asyncio
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import main as app_main
from app.database import Base, get_db
from app.models.backtest import BacktestRun
from app.services.analytics_backtests import resolve_blend_weights
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


def _curve(values: list[float]) -> list[dict[str, float | str]]:
    dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    return [{"date": date, "value": value} for date, value in zip(dates, values, strict=True)]


def _make_run(
    backtest_id: str,
    values: list[float],
    *,
    strategy_id: str = "trend_alpha",
    tickers: list[str] | None = None,
) -> BacktestRun:
    curve = _curve(values)
    benchmark = _curve([100_000.0, 100_300.0, 100_700.0, 101_000.0])
    return BacktestRun(
        id=backtest_id,
        workspace_id=TEST_WORKSPACE.id,
        created_by_user_id=TEST_USER.id,
        strategy_id=strategy_id,
        strategy_params={"lookback": 20},
        tickers=tickers or ["AAPL"],
        benchmark="SPY",
        start_date="2024-01-02",
        end_date="2024-01-05",
        initial_capital=100_000.0,
        slippage_bps=5.0,
        commission_per_share=0.005,
        market_impact_model="almgren_chriss",
        max_volume_participation_pct=5.0,
        position_sizing="equal_weight",
        portfolio_construction_model="equal_weight",
        portfolio_lookback_days=63,
        max_position_pct=25.0,
        max_gross_exposure_pct=150.0,
        turnover_limit_pct=100.0,
        max_sector_exposure_pct=100.0,
        allow_short_selling=False,
        max_short_position_pct=25.0,
        short_margin_requirement_pct=50.0,
        short_borrow_rate_bps=200.0,
        short_locate_fee_bps=10.0,
        short_squeeze_threshold_pct=15.0,
        rebalance_frequency="daily",
        equity_curve=curve,
        clean_equity_curve=curve,
        benchmark_curve=benchmark,
        drawdown_series=_curve([0.0, -0.5, -1.0, -0.2]),
        rolling_sharpe=_curve([1.0, 1.1, 1.2, 1.3]),
        rolling_volatility=_curve([10.0, 10.5, 11.0, 10.8]),
        monthly_returns=[{"year": 2024, "month": 1, "return_pct": 2.1}],
        metrics={"total_return_pct": 2.1, "sharpe_ratio": 1.3},
        benchmark_metrics={"total_return_pct": 1.0, "sharpe_ratio": 0.8},
    )


@contextmanager
def _build_client(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "analytics-api.db"
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
    install_auth_overrides(app)

    try:
        with TestClient(app) as client:
            yield client, session_factory
    finally:
        asyncio.run(_dispose())


async def _insert_runs(session_factory, *runs: BacktestRun):
    async with session_factory() as session:
        session.add_all(runs)
        await session.commit()


def test_compare_backtests_returns_correlation_matrix(monkeypatch, tmp_path):
    run_a = _make_run("cmp-a", [100_000.0, 102_000.0, 101_500.0, 103_500.0], tickers=["AAPL"])
    run_b = _make_run("cmp-b", [100_000.0, 99_500.0, 100_800.0, 101_200.0], tickers=["MSFT"])

    with _build_client(monkeypatch, tmp_path) as (client, session_factory):
        asyncio.run(_insert_runs(session_factory, run_a, run_b))

        response = client.post(
            "/api/analytics/compare",
            json={"backtest_ids": ["cmp-a", "cmp-b"]},
        )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["backtests"]] == ["cmp-a", "cmp-b"]
    assert len(payload["correlation_matrix"]) == 2
    assert all(len(row) == 2 for row in payload["correlation_matrix"])


def test_export_results_streams_csv(monkeypatch, tmp_path):
    run = _make_run("btcsv001", [100_000.0, 100_500.0, 101_500.0, 102_100.0])

    with _build_client(monkeypatch, tmp_path) as (client, session_factory):
        asyncio.run(_insert_runs(session_factory, run))
        response = client.get("/api/analytics/export/btcsv001?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == "attachment; filename=backtest_btcsv001.csv"
    assert "=== Configuration ===" in response.text
    assert "strategy,trend_alpha" in response.text
    assert "2024,1,2.1" in response.text


def test_monte_carlo_returns_percentile_payload(monkeypatch, tmp_path):
    run = _make_run("monte-001", [100_000.0, 101_200.0, 102_600.0, 103_000.0])

    with _build_client(monkeypatch, tmp_path) as (client, session_factory):
        asyncio.run(_insert_runs(session_factory, run))
        response = client.post("/api/analytics/monte-carlo/monte-001?n_simulations=250&n_days=63")

    assert response.status_code == 200
    payload = response.json()
    assert payload["n_simulations"] == 250
    assert payload["n_days"] == 63
    assert set(payload["percentiles"]) == {"p5", "p25", "p50", "p75", "p95"}


def test_portfolio_blend_pads_short_custom_weights(monkeypatch, tmp_path):
    run_a = _make_run("blend-a", [100_000.0, 101_000.0, 102_000.0, 103_000.0], tickers=["AAPL"])
    run_b = _make_run("blend-b", [100_000.0, 100_500.0, 101_000.0, 101_500.0], tickers=["MSFT"])
    run_c = _make_run("blend-c", [100_000.0, 99_000.0, 98_500.0, 99_500.0], tickers=["GOOGL"])

    with _build_client(monkeypatch, tmp_path) as (client, session_factory):
        asyncio.run(_insert_runs(session_factory, run_a, run_b, run_c))
        response = client.post(
            "/api/analytics/portfolio-blend",
            json={
                "backtest_ids": ["blend-a", "blend-b", "blend-c"],
                "weights": [1.0, 3.0],
                "optimize": "custom",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["weights"] == [0.25, 0.75, 0.0]
    assert len(payload["asset_contributions"]) == 3
    assert payload["equity_curve"][0]["date"] == "2024-01-03"


def test_min_drawdown_optimizer_prefers_lower_drawdown_curve():
    equities = pd.DataFrame(
        {
            "steady": [1.00, 1.01, 1.02, 1.03, 1.04],
            "crashy": [1.00, 1.20, 0.70, 0.75, 0.80],
        }
    )
    returns = equities.pct_change().dropna()

    weights = resolve_blend_weights(returns, equities, "min_dd", [])

    assert weights[0] > weights[1]
    assert weights[0] > 0.9
