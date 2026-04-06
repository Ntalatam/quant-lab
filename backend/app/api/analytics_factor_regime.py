from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_workspace
from app.database import get_db
from app.models.auth import Workspace
from app.schemas.analytics import FactorExposureResponse, RegimeAnalysisResponse
from app.schemas.common import ErrorResponse
from app.services.analytics_factor_regime import build_factor_exposure, build_regime_analysis

router = APIRouter()


@router.post(
    "/regime-analysis/{backtest_id}",
    response_model=RegimeAnalysisResponse,
    summary="Run regime analysis",
    description=(
        "Classifies the benchmark environment into trend, chop, high-volatility, "
        "and neutral regimes, then summarizes strategy performance inside each regime."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Backtest was not found."},
        422: {
            "model": ErrorResponse,
            "description": "Required market data could not be loaded.",
        },
    },
)
async def regime_analysis(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    return await build_regime_analysis(
        db,
        backtest_id,
        current_workspace.id,
    )


@router.post(
    "/factor-exposure/{backtest_id}",
    response_model=FactorExposureResponse,
    summary="Estimate factor exposures",
    description=(
        "Runs a multi-factor regression of strategy returns against market, size, "
        "value, and momentum proxies."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Backtest was not found."},
        422: {
            "model": ErrorResponse,
            "description": "Insufficient or missing factor data.",
        },
        500: {
            "model": ErrorResponse,
            "description": "Regression could not be completed.",
        },
    },
)
async def factor_exposure(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    return await build_factor_exposure(
        db,
        backtest_id,
        current_workspace.id,
    )
