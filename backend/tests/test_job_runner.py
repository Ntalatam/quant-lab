from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database import Base
from app.models.auth import User, Workspace, WorkspaceMembership
from app.services.backtest_runs import load_backtest_detail
from app.services.job_runner import ResearchJobWorker
from app.services.jobs import enqueue_research_job, get_research_job
from tests.auth_helpers import TEST_USER, TEST_WORKSPACE


def _build_result() -> dict:
    return {
        "id": "bt_job_001",
        "equity_curve": [
            {"date": "2024-01-02", "value": 100000.0},
            {"date": "2024-02-01", "value": 103250.0},
            {"date": "2024-05-01", "value": 118400.0},
        ],
        "clean_equity_curve": [{"date": "2024-01-02", "value": 100010.0}],
        "benchmark_curve": [{"date": "2024-01-02", "value": 100000.0}],
        "drawdown_series": [{"date": "2024-01-02", "value": 0.0}],
        "rolling_sharpe": [{"date": "2024-01-31", "value": 1.2}],
        "rolling_volatility": [{"date": "2024-01-31", "value": 12.5}],
        "monthly_returns": [{"year": 2024, "month": 1, "return_pct": 1.3}],
        "metrics": {"total_return_pct": 18.4, "sharpe_ratio": 1.42, "cagr_pct": 8.1},
        "benchmark_metrics": {"total_return_pct": 11.0, "sharpe_ratio": 0.9},
        "trades": [],
    }


def _build_config() -> dict:
    return {
        "strategy_id": "sma_crossover",
        "params": {"short_window": 20, "long_window": 60},
        "tickers": ["AAPL", "MSFT"],
        "benchmark": "SPY",
        "start_date": "2024-01-01",
        "end_date": "2024-05-01",
        "initial_capital": 100000,
        "slippage_bps": 5,
        "commission_per_share": 0.005,
        "market_impact_model": "almgren_chriss",
        "max_volume_participation_pct": 5,
        "position_sizing": "equal_weight",
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
        "rebalance_frequency": "daily",
    }


async def _seed_workspace(session_factory: async_sessionmaker[AsyncSession]):
    async with session_factory() as session:
        session.add(
            User(
                id=TEST_USER.id,
                email=TEST_USER.email,
                display_name=TEST_USER.display_name,
                password_hash="hash",
            )
        )
        session.add(
            Workspace(
                id=TEST_WORKSPACE.id,
                name=TEST_WORKSPACE.name,
                is_personal=TEST_WORKSPACE.is_personal,
            )
        )
        session.add(
            WorkspaceMembership(
                id="membership_1",
                workspace_id=TEST_WORKSPACE.id,
                user_id=TEST_USER.id,
                role="owner",
            )
        )
        await session.commit()


async def _load_job(session_factory: async_sessionmaker[AsyncSession], job_id: str):
    async with session_factory() as session:
        return await get_research_job(session, job_id)


async def _load_backtest(session_factory: async_sessionmaker[AsyncSession], backtest_id: str):
    async with session_factory() as session:
        return await load_backtest_detail(session, backtest_id)


def _build_session_factory(tmp_path: Path):
    db_path = tmp_path / "job-runner.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _prepare():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await _seed_workspace(session_factory)

    asyncio.run(_prepare())
    return engine, session_factory


def test_worker_completes_backtest_jobs_and_persists_results(monkeypatch, tmp_path):
    engine, session_factory = _build_session_factory(tmp_path)
    result = _build_result()

    async def fake_run_backtest(_db, _config, on_progress=None, workspace_id=None):
        assert workspace_id == TEST_WORKSPACE.id
        if on_progress is not None:
            await on_progress(25, 100, "2024-02-01", 103_250)
            await on_progress(100, 100, "2024-05-01", 118_400)
        return result

    monkeypatch.setattr("app.services.job_runner.run_backtest", fake_run_backtest)

    async def _exercise():
        async with session_factory() as session:
            job = await enqueue_research_job(
                session,
                kind="backtest_run",
                request_payload=_build_config(),
                workspace_id=TEST_WORKSPACE.id,
                created_by_user_id=TEST_USER.id,
            )
            await session.commit()
            job_id = job.id

        worker = ResearchJobWorker(session_factory, poll_interval_seconds=0.01)
        claimed = await worker.run_once()
        assert claimed is True

        stored_job = await _load_job(session_factory, job_id)
        assert stored_job is not None
        assert stored_job.status == "completed"
        assert stored_job.result_backtest_run_id == result["id"]
        assert stored_job.progress_pct == 1.0
        assert stored_job.progress_current == 100
        assert stored_job.progress_total == 100
        assert any("completed" in entry["message"].lower() for entry in stored_job.logs)

        detail = await _load_backtest(session_factory, result["id"])
        assert detail is not None
        run, trades = detail
        assert run.workspace_id == TEST_WORKSPACE.id
        assert run.created_by_user_id == TEST_USER.id
        assert trades == []

        await engine.dispose()

    asyncio.run(_exercise())


def test_worker_persists_failures_for_backtest_jobs(monkeypatch, tmp_path):
    engine, session_factory = _build_session_factory(tmp_path)

    async def fake_run_backtest(_db, _config, on_progress=None, workspace_id=None):
        raise ValueError("No market data was returned.")

    monkeypatch.setattr("app.services.job_runner.run_backtest", fake_run_backtest)

    async def _exercise():
        async with session_factory() as session:
            job = await enqueue_research_job(
                session,
                kind="backtest_run",
                request_payload=_build_config(),
                workspace_id=TEST_WORKSPACE.id,
                created_by_user_id=TEST_USER.id,
            )
            await session.commit()
            job_id = job.id

        worker = ResearchJobWorker(session_factory, poll_interval_seconds=0.01)
        claimed = await worker.run_once()
        assert claimed is True

        stored_job = await _load_job(session_factory, job_id)
        assert stored_job is not None
        assert stored_job.status == "failed"
        assert "No market data was returned." in (stored_job.error_message or "")
        assert stored_job.failed_at is not None

        await engine.dispose()

    asyncio.run(_exercise())
