from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class DemoStatusResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tickers_loaded": 4,
                "total_tickers": 4,
                "backtests_exist": True,
                "seeded": True,
            }
        }
    )

    tickers_loaded: int
    total_tickers: int
    backtests_exist: bool
    seeded: bool


class DemoSeedResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "tickers_loaded": ["SPY", "AAPL", "MSFT", "GLD"],
                "tickers_failed": [],
                "backtests_created": ["bt_demo_001", "bt_demo_002"],
                "errors": [],
            }
        }
    )

    status: Literal["ok", "partial", "already_seeded"]
    tickers_loaded: list[str]
    tickers_failed: list[str]
    backtests_created: list[str]
    errors: list[str]
