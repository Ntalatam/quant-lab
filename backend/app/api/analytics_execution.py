from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_workspace
from app.database import get_db
from app.models.auth import Workspace
from app.schemas.analytics import CapacityResponse, TransactionCostAnalysisResponse
from app.schemas.common import ErrorResponse
from app.services.analytics_execution import (
    build_capacity_analysis,
    build_transaction_cost_analysis,
)

router = APIRouter()


@router.post(
    "/capacity/{backtest_id}",
    response_model=CapacityResponse,
    summary="Estimate strategy capacity",
    description=(
        "Estimates how much capital a strategy can absorb before its trade size "
        "becomes an excessive share of average daily volume."
    ),
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def capacity_analysis(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    return await build_capacity_analysis(
        db,
        backtest_id,
        current_workspace.id,
    )


@router.post(
    "/tca/{backtest_id}",
    response_model=TransactionCostAnalysisResponse,
    summary="Analyze transaction costs",
    description=(
        "Aggregates commissions, spread, impact, timing, opportunity costs, "
        "and fill-quality metrics for a saved backtest."
    ),
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def transaction_cost_analysis(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    return await build_transaction_cost_analysis(
        db,
        backtest_id,
        current_workspace.id,
    )
