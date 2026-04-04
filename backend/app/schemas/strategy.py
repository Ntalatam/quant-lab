from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrategyParamDefinition(BaseModel):
    name: str = Field(description="Machine-readable parameter identifier.")
    label: str = Field(description="UI-friendly parameter label.")
    type: Literal["int", "float", "select", "bool"] = Field(
        description="Form control type to render for this parameter."
    )
    default: int | float | str | bool = Field(
        description="Default value used when no override is supplied."
    )
    min: float | int | None = Field(default=None, description="Optional lower bound.")
    max: float | int | None = Field(default=None, description="Optional upper bound.")
    step: float | int | None = Field(default=None, description="Optional increment.")
    options: list[str] | None = Field(
        default=None,
        description="Selectable values for enum-like parameters.",
    )
    description: str = Field(description="What the parameter controls.")


class StrategyInfoResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "sma_crossover",
                "name": "SMA Crossover",
                "description": "Trend-following strategy using fast and slow moving averages.",
                "category": "trend_following",
                "signal_mode": "long_only",
                "requires_short_selling": False,
                "params": [
                    {
                        "name": "short_window",
                        "label": "Short Window",
                        "type": "int",
                        "default": 20,
                        "min": 5,
                        "max": 100,
                        "step": 1,
                        "options": None,
                        "description": "Fast moving-average lookback in bars.",
                    }
                ],
            }
        }
    )

    id: str
    name: str
    description: str
    category: str
    source_type: Literal["builtin", "custom"] = "builtin"
    signal_mode: Literal["long_only", "long_short"]
    requires_short_selling: bool
    params: list[StrategyParamDefinition]


class StrategyParamsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "sma_crossover",
                "name": "SMA Crossover",
                "params": [
                    {
                        "name": "short_window",
                        "label": "Short Window",
                        "type": "int",
                        "default": 20,
                        "min": 5,
                        "max": 100,
                        "step": 1,
                        "options": None,
                        "description": "Fast moving-average lookback in bars.",
                    }
                ],
                "defaults": {
                    "short_window": 20,
                    "long_window": 60,
                },
            }
        }
    )

    id: str
    name: str
    source_type: Literal["builtin", "custom"] = "builtin"
    params: list[StrategyParamDefinition]
    defaults: dict[str, int | float | str | bool]


class StrategyEditorHelper(BaseModel):
    name: str
    signature: str
    description: str


class StrategyEditorSpecResponse(BaseModel):
    template: str
    rules: list[str]
    helpers: list[StrategyEditorHelper]


class CustomStrategyValidateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20000)


class CustomStrategyValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    extracted: StrategyParamsResponse | None = None
    preview: StrategyInfoResponse | None = None


class CustomStrategyCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20000)


class CustomStrategyUpdateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20000)


class CustomStrategyDetailResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    source_type: Literal["custom"] = "custom"
    signal_mode: Literal["long_only", "long_short"]
    requires_short_selling: bool
    params: list[StrategyParamDefinition]
    defaults: dict[str, int | float | str | bool]
    code: str
    created_at: str
    updated_at: str


class CustomStrategySummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    source_type: Literal["custom"] = "custom"
    signal_mode: Literal["long_only", "long_short"]
    requires_short_selling: bool
    params: list[StrategyParamDefinition]
    created_at: str
    updated_at: str


class DeleteCustomStrategyResponse(BaseModel):
    deleted: bool = True
    id: str
