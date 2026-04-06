from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.datetime import utc_now_naive

if TYPE_CHECKING:
    from app.models.auth import User, Workspace
    from app.models.backtest import BacktestRun


class ResearchJob(Base):
    __tablename__ = "research_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id"),
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(48), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True, default="queued")
    request_payload: Mapped[dict] = mapped_column(JSON)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    result_backtest_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("backtest_runs.id"),
        nullable=True,
        index=True,
        default=None,
    )
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    progress_date: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)
    progress_equity: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    logs: Mapped[list[dict]] = mapped_column(JSON, default=list)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)
    queued_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

    workspace: Mapped[Workspace] = relationship()
    created_by_user: Mapped[User] = relationship()
    result_backtest_run: Mapped[BacktestRun | None] = relationship()
