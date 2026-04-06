from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.analytics import (
    CorrelationRequest,
    CorrelationResponse,
    SpreadRequest,
    SpreadResponse,
)
from app.schemas.common import ErrorResponse
from app.services.analytics_market import build_correlation_response, build_spread_response

router = APIRouter()


@router.post(
    "/correlation",
    response_model=CorrelationResponse,
    summary="Correlation matrix & cointegration analysis",
    description=(
        "Loads OHLCV data for the requested tickers, computes a static "
        "correlation matrix, rolling pairwise correlations, and runs "
        "Engle-Granger cointegration tests to discover tradeable pairs."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request parameters."},
        422: {
            "model": ErrorResponse,
            "description": "Could not load data for one or more tickers.",
        },
    },
)
async def correlation_analysis(
    payload: CorrelationRequest,
    db: AsyncSession = Depends(get_db),
):
    return await build_correlation_response(db, payload)


@router.post(
    "/spread",
    response_model=SpreadResponse,
    summary="Spread analysis for a ticker pair",
    description=(
        "Computes the log-price-ratio spread, rolling z-score, half-life of "
        "mean reversion, and Engle-Granger cointegration test for a specific pair."
    ),
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Could not load data for one or both tickers.",
        },
    },
)
async def spread_analysis(
    payload: SpreadRequest,
    db: AsyncSession = Depends(get_db),
):
    return await build_spread_response(db, payload)
