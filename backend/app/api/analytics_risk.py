from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_workspace
from app.database import get_db
from app.models.auth import Workspace
from app.schemas.analytics import RiskBudgetResponse
from app.schemas.common import ErrorResponse
from app.services.analytics_risk import build_risk_budget_response

router = APIRouter()


@router.post(
    "/risk-budget/{backtest_id}",
    response_model=RiskBudgetResponse,
    summary="Build a risk budgeting dashboard",
    description=(
        "Reconstructs the latest non-flat portfolio snapshot from a saved backtest, "
        "decomposes one-day VaR / CVaR by position, and stress-tests that book "
        "through 2008, COVID, and 2022 rate-shock regimes."
    ),
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def risk_budget_analysis(
    backtest_id: str,
    lookback_days: int = Query(63, ge=21, le=252),
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    return await build_risk_budget_response(
        db,
        backtest_id,
        current_workspace.id,
        lookback_days=lookback_days,
    )
