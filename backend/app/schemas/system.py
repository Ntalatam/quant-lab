from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DependencyHealth(BaseModel):
    status: Literal["ok", "degraded"]
    latency_ms: float | None = Field(
        default=None,
        description="Best-effort dependency probe latency in milliseconds.",
    )
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "service": "quantlab-backend",
                "environment": "development",
                "version": "1.0.0",
                "timestamp": "2026-04-03T12:00:00Z",
                "uptime_seconds": 532.41,
                "request_id": "req_93f1b2c8",
                "dependencies": {
                    "database": {
                        "status": "ok",
                        "latency_ms": 4.12,
                        "details": {"engine": "sqlalchemy-async"},
                    },
                    "paper_trading": {
                        "status": "ok",
                        "latency_ms": None,
                        "details": {
                            "runtime_sessions": 2,
                            "subscriber_channels": 1,
                        },
                    },
                },
            }
        }
    )

    status: Literal["ok", "degraded"]
    service: str
    environment: str
    version: str
    timestamp: datetime
    uptime_seconds: float
    request_id: str | None = None
    dependencies: dict[str, DependencyHealth]
