from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Backtest not found",
            }
        }
    )

    detail: str = Field(description="Human-readable error message.")


class DeleteResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "deleted",
            }
        }
    )

    status: Literal["deleted"]


class StatusMessageResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "message": "Operation completed successfully.",
            }
        }
    )

    status: str
    message: str | None = None
