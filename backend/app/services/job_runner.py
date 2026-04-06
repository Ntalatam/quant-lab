from __future__ import annotations

import asyncio
import socket
import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.observability import elapsed_ms, get_logger
from app.schemas.backtest import (
    BacktestConfig,
    BacktestSweep2DConfig,
    BacktestSweepConfig,
    BayesOptConfig,
    WalkForwardRequest,
)
from app.services.backtest_engine import run_backtest
from app.services.backtest_runs import persist_backtest_result
from app.services.data_ingestion import ensure_data_loaded
from app.services.jobs import ResearchJobService
from app.services.parallel import run_in_thread_pool
from app.services.walk_forward import run_walk_forward

logger = get_logger(__name__)


class ResearchJobWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        worker_id: str | None = None,
        poll_interval_seconds: float | None = None,
    ):
        self._session_factory = session_factory
        self._jobs = ResearchJobService(session_factory)
        self._worker_id = worker_id or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self._poll_interval_seconds = (
            poll_interval_seconds or settings.JOB_WORKER_POLL_INTERVAL_SECONDS
        )
        self._shutdown = asyncio.Event()

    async def run_forever(self):
        logger.info("jobs.worker.started", worker_id=self._worker_id)
        while not self._shutdown.is_set():
            claimed = await self.run_once()
            if not claimed:
                try:
                    await asyncio.wait_for(
                        self._shutdown.wait(),
                        timeout=self._poll_interval_seconds,
                    )
                except TimeoutError:
                    continue
        logger.info("jobs.worker.stopped", worker_id=self._worker_id)

    async def run_once(self) -> bool:
        job = await self._jobs.claim_next_job(self._worker_id)
        if job is None:
            return False

        start_time = time.perf_counter()
        log = logger.bind(job_id=job.id, kind=job.kind, worker_id=self._worker_id)
        log.info("jobs.worker.claimed")
        try:
            await self._execute_job(job)
            log.info("jobs.worker.completed", duration_ms=elapsed_ms(start_time))
        except Exception as exc:
            log.exception("jobs.worker.failed", duration_ms=elapsed_ms(start_time), error=str(exc))
            await self._jobs.fail_job(
                job.id,
                error_message=str(exc),
                append_log_message=f"Job failed: {exc}",
            )
        return True

    async def shutdown(self):
        self._shutdown.set()

    async def _execute_job(self, job):
        if job.kind == "backtest_run":
            await self._run_backtest_job(job)
            return
        if job.kind == "backtest_sweep":
            await self._run_sweep_job(job)
            return
        if job.kind == "backtest_sweep2d":
            await self._run_sweep2d_job(job)
            return
        if job.kind == "backtest_walk_forward":
            await self._run_walk_forward_job(job)
            return
        if job.kind == "backtest_optimize":
            await self._run_optimize_job(job)
            return
        raise ValueError(f"Unsupported job kind: {job.kind}")

    async def _preload_market_data(self, db: AsyncSession, config: BacktestConfig):
        from datetime import date

        start = date.fromisoformat(config.start_date)
        end = date.fromisoformat(config.end_date)
        for ticker in set(config.tickers + [config.benchmark]):
            loaded = await ensure_data_loaded(db, ticker, start, end)
            if not loaded:
                raise ValueError(f"Could not load data for {ticker}")

    async def _run_backtest_job(self, job):
        config = BacktestConfig(**job.request_payload)

        async def on_progress(bar_num: int, total_bars: int, date_str: str, equity: float):
            pct = bar_num / total_bars if total_bars else 0.0
            await self._jobs.update_progress(
                job.id,
                progress_pct=pct,
                progress_current=bar_num,
                progress_total=total_bars,
                progress_message=f"Simulating {bar_num} of {total_bars} bars",
                progress_date=date_str,
                progress_equity=equity,
            )

        async with self._session_factory() as db:
            result = await run_backtest(
                db,
                config,
                on_progress=on_progress,
                workspace_id=job.workspace_id,
            )
            run, _ = await persist_backtest_result(
                db,
                config,
                result,
                workspace_id=job.workspace_id,
                created_by_user_id=job.created_by_user_id,
            )

        await self._jobs.update_progress(
            job.id,
            progress_pct=1.0,
            progress_message="Persisting completed backtest result.",
        )
        await self._jobs.complete_job(
            job.id,
            result_payload={"backtest_run_id": run.id},
            result_backtest_run_id=run.id,
            append_log_message="Backtest completed.",
        )

    async def _run_sweep_job(self, job):
        payload = BacktestSweepConfig(**job.request_payload)
        results: list[dict[str, Any]] = []
        total = len(payload.sweep_values)

        async with self._session_factory() as db:
            await self._preload_market_data(db, payload.base_config)

        for index, value in enumerate(payload.sweep_values, start=1):
            params = dict(payload.base_config.params)
            params[payload.sweep_param] = value
            sweep_config = payload.base_config.model_copy(update={"params": params})
            try:
                async with self._session_factory() as db:
                    result = await run_backtest(
                        db,
                        sweep_config,
                        workspace_id=job.workspace_id,
                    )
                results.append(
                    {
                        "param_value": value,
                        "sharpe_ratio": result["metrics"]["sharpe_ratio"],
                        "total_return_pct": result["metrics"]["total_return_pct"],
                        "max_drawdown_pct": result["metrics"]["max_drawdown_pct"],
                        "cagr_pct": result["metrics"]["cagr_pct"],
                    }
                )
            except Exception as exc:
                results.append({"param_value": value, "error": str(exc)})

            await self._jobs.update_progress(
                job.id,
                progress_pct=index / total if total else 1.0,
                progress_current=index,
                progress_total=total,
                progress_message=f"Completed {index} of {total} sweep runs",
            )

        await self._jobs.complete_job(
            job.id,
            result_payload={
                "sweep_param": payload.sweep_param,
                "results": results,
            },
            append_log_message="Parameter sweep completed.",
        )

    async def _run_sweep2d_job(self, job):
        payload = BacktestSweep2DConfig(**job.request_payload)
        grid = [(vx, vy) for vx in payload.values_x for vy in payload.values_y]
        total = len(grid)
        flat_results: list[dict[str, Any]] = []

        async with self._session_factory() as db:
            await self._preload_market_data(db, payload.base_config)

        for index, (value_x, value_y) in enumerate(grid, start=1):
            params = dict(payload.base_config.params)
            params[payload.param_x] = value_x
            params[payload.param_y] = value_y
            sweep_config = payload.base_config.model_copy(update={"params": params})

            try:
                async with self._session_factory() as db:
                    result = await run_backtest(
                        db,
                        sweep_config,
                        workspace_id=job.workspace_id,
                    )
                flat_results.append(
                    {
                        "x": value_x,
                        "y": value_y,
                        "value": result["metrics"].get(payload.metric),
                        "total_return_pct": result["metrics"].get("total_return_pct"),
                        "max_drawdown_pct": result["metrics"].get("max_drawdown_pct"),
                    }
                )
            except Exception as exc:
                flat_results.append(
                    {
                        "x": value_x,
                        "y": value_y,
                        "value": None,
                        "error": str(exc),
                    }
                )

            await self._jobs.update_progress(
                job.id,
                progress_pct=index / total if total else 1.0,
                progress_current=index,
                progress_total=total,
                progress_message=f"Completed {index} of {total} heatmap cells",
            )

        row_size = len(payload.values_y)
        cells = [
            flat_results[idx : idx + row_size] for idx in range(0, len(flat_results), row_size)
        ]
        await self._jobs.complete_job(
            job.id,
            result_payload={
                "param_x": payload.param_x,
                "param_y": payload.param_y,
                "metric": payload.metric,
                "values_x": payload.values_x,
                "values_y": payload.values_y,
                "cells": cells,
            },
            append_log_message="2D sweep completed.",
        )

    async def _run_walk_forward_job(self, job):
        payload = WalkForwardRequest(**job.request_payload)

        async with self._session_factory() as db:
            await self._preload_market_data(db, payload.config)

        async def on_progress(fold_num: int, total_folds: int, message: str):
            await self._jobs.update_progress(
                job.id,
                progress_pct=fold_num / total_folds if total_folds else 1.0,
                progress_current=fold_num,
                progress_total=total_folds,
                progress_message=message,
            )

        async with self._session_factory() as db:
            result = await run_walk_forward(
                db,
                payload.config,
                n_folds=payload.n_folds,
                train_pct=payload.train_pct,
                workspace_id=job.workspace_id,
                on_progress=on_progress,
            )

        await self._jobs.complete_job(
            job.id,
            result_payload=result,
            append_log_message="Walk-forward analysis completed.",
        )

    async def _run_optimize_job(self, job):
        payload = BayesOptConfig(**job.request_payload)
        try:
            import optuna

            optuna.logging.set_verbosity(optuna.logging.WARNING)
        except ImportError as exc:
            raise RuntimeError("optuna is not installed. Run: pip install optuna") from exc

        async with self._session_factory() as db:
            await self._preload_market_data(db, payload.base_config)

        trials_log: list[dict[str, Any]] = []
        n_trials = min(payload.n_trials, 50)

        def objective(trial: Any) -> float:
            params = dict(payload.base_config.params)
            for spec in payload.param_specs:
                if spec.type == "int":
                    step = int(spec.step) if spec.step else 1
                    params[spec.name] = trial.suggest_int(
                        spec.name,
                        int(spec.low),
                        int(spec.high),
                        step=step,
                    )
                else:
                    params[spec.name] = trial.suggest_float(
                        spec.name,
                        spec.low,
                        spec.high,
                        step=spec.step,
                    )

            trial_config = payload.base_config.model_copy(update={"params": params})

            async def _run_trial():
                async with self._session_factory() as db:
                    return await run_backtest(
                        db,
                        trial_config,
                        workspace_id=job.workspace_id,
                    )

            try:
                result = asyncio.run(_run_trial())
            except Exception:
                return float("-inf") if payload.maximize else float("inf")

            metric_value = result["metrics"].get(payload.metric)
            if metric_value is None:
                return float("-inf") if payload.maximize else float("inf")

            trials_log.append(
                {
                    "trial": trial.number,
                    "params": dict(params),
                    "value": float(metric_value),
                }
            )
            asyncio.run(
                self._jobs.update_progress(
                    job.id,
                    progress_pct=len(trials_log) / n_trials if n_trials else 1.0,
                    progress_current=len(trials_log),
                    progress_total=n_trials,
                    progress_message=f"Completed trial {len(trials_log)} of {n_trials}",
                )
            )
            return float(metric_value) if payload.maximize else -float(metric_value)

        def run_study():
            direction = "maximize" if payload.maximize else "minimize"
            study = optuna.create_study(direction=direction)
            study.optimize(objective, n_trials=n_trials, n_jobs=1)
            return study

        study = await run_in_thread_pool(run_study)
        best_params = dict(payload.base_config.params)
        best_params.update(study.best_params)
        best_value = study.best_value if payload.maximize else -study.best_value
        trials_sorted = sorted(trials_log, key=lambda item: int(item["trial"]))

        await self._jobs.complete_job(
            job.id,
            result_payload={
                "best_params": best_params,
                "best_value": round(float(best_value), 4),
                "metric": payload.metric,
                "n_trials": len(trials_sorted),
                "trials": trials_sorted,
                "param_specs": [spec.model_dump() for spec in payload.param_specs],
            },
            append_log_message="Bayesian optimization completed.",
        )
