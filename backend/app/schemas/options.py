"""Pydantic schemas for the options analytics endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ── Pricing request / response ────────────────────────────────────────────


class OptionPriceRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "spot": 150.0,
                "strike": 155.0,
                "days_to_expiry": 30,
                "risk_free_rate": 0.05,
                "volatility": 0.25,
                "option_type": "call",
            }
        }
    )

    spot: float = Field(gt=0, description="Current underlying price")
    strike: float = Field(gt=0, description="Strike price")
    days_to_expiry: int = Field(ge=0, le=3650, description="Days until expiration")
    risk_free_rate: float = Field(ge=0, le=1, description="Annualized risk-free rate")
    volatility: float = Field(gt=0, le=5, description="Annualized implied volatility")
    option_type: Literal["call", "put"] = "call"


class OptionPriceResponse(BaseModel):
    price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    intrinsic: float
    time_value: float
    option_type: str
    moneyness: float
    moneyness_label: str


# ── Implied volatility ────────────────────────────────────────────────────


class ImpliedVolRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "market_price": 5.50,
                "spot": 150.0,
                "strike": 155.0,
                "days_to_expiry": 30,
                "risk_free_rate": 0.05,
                "option_type": "call",
            }
        }
    )

    market_price: float = Field(gt=0, description="Observed market price of the option")
    spot: float = Field(gt=0)
    strike: float = Field(gt=0)
    days_to_expiry: int = Field(ge=1, le=3650)
    risk_free_rate: float = Field(ge=0, le=1)
    option_type: Literal["call", "put"] = "call"


class ImpliedVolResponse(BaseModel):
    implied_volatility: float | None
    implied_volatility_pct: float | None
    market_price: float
    theoretical_price: float | None
    message: str


# ── Options chain ─────────────────────────────────────────────────────────


class ChainRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "spot": 150.0,
                "risk_free_rate": 0.05,
                "volatility": 0.25,
                "days_to_expiry": [30, 60, 90],
            }
        }
    )

    spot: float = Field(gt=0)
    risk_free_rate: float = Field(ge=0, le=1, default=0.05)
    volatility: float = Field(gt=0, le=5, default=0.25)
    days_to_expiry: list[int] = Field(
        default=[30, 60, 90],
        min_length=1,
        description="List of days-to-expiry for each expiration",
    )
    strike_range_pct: float = Field(ge=0.05, le=0.50, default=0.20)
    n_strikes: int = Field(ge=5, le=51, default=15)


class ChainEntry(BaseModel):
    dte: int
    strike: float
    call_price: float
    call_delta: float
    call_gamma: float
    call_theta: float
    call_vega: float
    put_price: float
    put_delta: float
    put_gamma: float
    put_theta: float
    put_vega: float
    moneyness: float


class ChainResponse(BaseModel):
    spot: float
    chain: list[ChainEntry]


# ── Volatility surface ────────────────────────────────────────────────────


class VolSurfaceRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "spot": 150.0,
                "risk_free_rate": 0.05,
                "base_volatility": 0.25,
            }
        }
    )

    spot: float = Field(gt=0)
    risk_free_rate: float = Field(ge=0, le=1, default=0.05)
    base_volatility: float = Field(gt=0, le=5, default=0.25)
    days_to_expiry: list[int] | None = Field(
        default=None,
        description="Custom expiry list; defaults to [7, 14, 30, 60, 90, 120, 180, 365]",
    )
    n_strikes: int = Field(ge=5, le=51, default=21)
    strike_range_pct: float = Field(ge=0.05, le=0.50, default=0.25)


class VolSurfacePoint(BaseModel):
    dte: int
    strike: float
    moneyness: float
    implied_vol: float


class VolSurfaceResponse(BaseModel):
    spot: float
    base_vol: float
    strikes: list[float]
    expiries: list[int]
    surface: list[VolSurfacePoint]


# ── P&L scenario ──────────────────────────────────────────────────────────


class PnlScenarioRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "spot": 150.0,
                "strike": 155.0,
                "days_to_expiry": 30,
                "risk_free_rate": 0.05,
                "volatility": 0.25,
                "option_type": "call",
                "position": 1,
            }
        }
    )

    spot: float = Field(gt=0)
    strike: float = Field(gt=0)
    days_to_expiry: int = Field(ge=1, le=3650)
    risk_free_rate: float = Field(ge=0, le=1, default=0.05)
    volatility: float = Field(gt=0, le=5, default=0.25)
    option_type: Literal["call", "put"] = "call"
    position: Literal[1, -1] = Field(default=1, description="1 = long, -1 = short")
    entry_price: float | None = Field(default=None, description="Override entry premium")
    price_range_pct: float = Field(ge=0.05, le=0.50, default=0.15)


class PnlPoint(BaseModel):
    spot: float
    pnl: float


class PnlCurve(BaseModel):
    dte: int
    label: str
    points: list[PnlPoint]


class PnlScenarioResponse(BaseModel):
    strike: float
    entry_price: float
    position: str
    option_type: str
    curves: list[PnlCurve]
