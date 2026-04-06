from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.models.job import ResearchJob
from app.utils.datetime import utc_now_naive

TERMINAL_JOB_STATUSES = {"completed", "failed"}
ACTIVE_JOB_STATUSES = {"queued", "running"}


def append_job_log(
    logs: list[dict[str, Any]] | None,
    message: str,
    *,
    timestamp: datetime | None = None,
) -> list[dict[str, Any]]:
    entries = list(logs or [])
    entries.append(
        {
            "timestamp": (timestamp or utc_now_naive()).isoformat(),
            "message": message,
        }
    )
    return entries


def serialize_job(job: ResearchJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "progress_pct": round(job.progress_pct or 0.0, 4),
        "progress_current": job.progress_current or 0,
        "progress_total": job.progress_total or 0,
        "progress_message": job.progress_message,
        "progress_date": job.progress_date,
        "progress_equity": round(job.progress_equity, 2)
        if job.progress_equity is not None
        else None,
        "logs": job.logs or [],
        "attempt_count": job.attempt_count or 0,
        "max_attempts": job.max_attempts or 1,
        "result_backtest_run_id": job.result_backtest_run_id,
        "result": job.result_payload,
        "error_message": job.error_message,
        "queued_at": job.queued_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "failed_at": job.failed_at,
        "updated_at": job.updated_at,
    }


async def enqueue_research_job(
    db: AsyncSession,
    *,
    kind: str,
    request_payload: dict[str, Any],
    workspace_id: str,
    created_by_user_id: str,
    max_attempts: int | None = None,
    progress_message: str | None = None,
) -> ResearchJob:
    now = utc_now_naive()
    job = ResearchJob(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        created_by_user_id=created_by_user_id,
        kind=kind,
        status="queued",
        request_payload=jsonable_encoder(request_payload),
        progress_pct=0.0,
        progress_current=0,
        progress_total=0,
        progress_message=progress_message or "Queued for worker pickup.",
        logs=append_job_log(None, "Job queued."),
        attempt_count=0,
        max_attempts=max_attempts or settings.JOB_MAX_ATTEMPTS,
        queued_at=now,
        updated_at=now,
    )
    db.add(job)
    await db.flush()
    return job


async def get_research_job(
    db: AsyncSession,
    job_id: str,
    *,
    workspace_id: str | None = None,
) -> ResearchJob | None:
    query: Select[tuple[ResearchJob]] = select(ResearchJob).where(ResearchJob.id == job_id)
    if workspace_id is not None:
        query = query.where(ResearchJob.workspace_id == workspace_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_research_jobs(
    db: AsyncSession,
    *,
    workspace_id: str,
    limit: int = 50,
) -> list[ResearchJob]:
    result = await db.execute(
        select(ResearchJob)
        .where(ResearchJob.workspace_id == workspace_id)
        .order_by(ResearchJob.queued_at.desc(), ResearchJob.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


class ResearchJobService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def fetch_job(self, job_id: str) -> ResearchJob | None:
        async with self._session_factory() as db:
            return await get_research_job(db, job_id)

    async def claim_next_job(self, worker_id: str) -> ResearchJob | None:
        async with self._session_factory() as db:
            next_id = await db.scalar(
                select(ResearchJob.id)
                .where(ResearchJob.status == "queued")
                .order_by(ResearchJob.queued_at.asc(), ResearchJob.id.asc())
                .limit(1)
            )
            if next_id is None:
                return None

            now = utc_now_naive()
            result = await db.execute(
                update(ResearchJob)
                .where(ResearchJob.id == next_id, ResearchJob.status == "queued")
                .values(
                    status="running",
                    worker_id=worker_id,
                    attempt_count=ResearchJob.attempt_count + 1,
                    started_at=now,
                    updated_at=now,
                )
            )
            if (getattr(result, "rowcount", 0) or 0) == 0:
                await db.rollback()
                return None

            job = await get_research_job(db, next_id)
            if job is None:
                await db.rollback()
                return None
            job.logs = append_job_log(job.logs, "Job claimed by worker.", timestamp=now)
            job.progress_message = job.progress_message or "Worker started processing."
            await db.commit()
            return job

    async def update_progress(
        self,
        job_id: str,
        *,
        progress_pct: float | None = None,
        progress_current: int | None = None,
        progress_total: int | None = None,
        progress_message: str | None = None,
        progress_date: str | None = None,
        progress_equity: float | None = None,
        append_log_message: str | None = None,
    ) -> ResearchJob | None:
        async with self._session_factory() as db:
            job = await get_research_job(db, job_id)
            if job is None:
                return None

            job.status = "running"
            if progress_pct is not None:
                job.progress_pct = max(0.0, min(1.0, float(progress_pct)))
            if progress_current is not None:
                job.progress_current = int(progress_current)
            if progress_total is not None:
                job.progress_total = int(progress_total)
            if progress_message is not None:
                job.progress_message = progress_message
            if progress_date is not None:
                job.progress_date = progress_date
            if progress_equity is not None:
                job.progress_equity = float(progress_equity)
            if append_log_message:
                job.logs = append_job_log(job.logs, append_log_message)
            job.updated_at = utc_now_naive()
            await db.commit()
            return job

    async def complete_job(
        self,
        job_id: str,
        *,
        result_payload: dict[str, Any] | None = None,
        result_backtest_run_id: str | None = None,
        append_log_message: str | None = None,
    ) -> ResearchJob | None:
        async with self._session_factory() as db:
            job = await get_research_job(db, job_id)
            if job is None:
                return None

            now = utc_now_naive()
            job.status = "completed"
            job.progress_pct = 1.0
            if append_log_message:
                job.logs = append_job_log(job.logs, append_log_message, timestamp=now)
            job.result_payload = (
                jsonable_encoder(result_payload) if result_payload is not None else None
            )
            job.result_backtest_run_id = result_backtest_run_id
            job.error_message = None
            job.completed_at = now
            job.failed_at = None
            job.updated_at = now
            await db.commit()
            return job

    async def fail_job(
        self,
        job_id: str,
        *,
        error_message: str,
        append_log_message: str | None = None,
    ) -> ResearchJob | None:
        async with self._session_factory() as db:
            job = await get_research_job(db, job_id)
            if job is None:
                return None

            now = utc_now_naive()
            job.status = "failed"
            job.error_message = error_message
            job.progress_message = append_log_message or error_message
            job.failed_at = now
            job.completed_at = None
            job.updated_at = now
            job.logs = append_job_log(
                job.logs,
                append_log_message or f"Job failed: {error_message}",
                timestamp=now,
            )
            await db.commit()
            return job
