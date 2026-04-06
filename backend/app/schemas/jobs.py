from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ResearchJobKind = Literal[
    "backtest_run",
    "backtest_sweep",
    "backtest_sweep2d",
    "backtest_walk_forward",
    "backtest_optimize",
]
ResearchJobStatus = Literal["queued", "running", "completed", "failed"]


class ResearchJobLogEntry(BaseModel):
    timestamp: datetime
    message: str


class ResearchJobResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "job_123",
                "kind": "backtest_run",
                "status": "running",
                "progress_pct": 0.42,
                "progress_current": 42,
                "progress_total": 100,
                "progress_message": "Simulating 42 of 100 bars",
                "progress_date": "2024-03-01",
                "progress_equity": 103250.0,
                "logs": [
                    {
                        "timestamp": "2026-04-05T17:00:00Z",
                        "message": "Job claimed by worker.",
                    }
                ],
                "attempt_count": 1,
                "max_attempts": 1,
                "result_backtest_run_id": None,
                "result": None,
                "error_message": None,
                "queued_at": "2026-04-05T16:59:58Z",
                "started_at": "2026-04-05T17:00:00Z",
                "completed_at": None,
                "failed_at": None,
                "updated_at": "2026-04-05T17:00:02Z",
            }
        }
    )

    id: str
    kind: ResearchJobKind | str
    status: ResearchJobStatus | str
    progress_pct: float = 0.0
    progress_current: int = 0
    progress_total: int = 0
    progress_message: str | None = None
    progress_date: str | None = None
    progress_equity: float | None = None
    logs: list[ResearchJobLogEntry] = Field(default_factory=list)
    attempt_count: int = 0
    max_attempts: int = 1
    result_backtest_run_id: str | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    updated_at: datetime


class ResearchJobListResponse(BaseModel):
    items: list[ResearchJobResponse]
