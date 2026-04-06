from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_workspace
from app.database import get_db
from app.models.auth import Workspace
from app.schemas.analytics import (
    CompareRequest,
    ComparisonResponse,
    MonteCarloResult,
    PortfolioBlendRequest,
    PortfolioBlendResponse,
)
from app.schemas.common import ErrorResponse
from app.services.analytics_compare import (
    build_backtest_export,
    build_comparison_response,
    build_monte_carlo_response,
    build_portfolio_blend_response,
)

router = APIRouter()


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    summary="Compare multiple backtests",
    description=(
        "Loads multiple saved backtests, aligns their equity curves, and returns "
        "a comparison bundle including the return-correlation matrix."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "At least two backtests are required.",
        },
        404: {
            "model": ErrorResponse,
            "description": "One of the requested backtests was not found.",
        },
    },
)
async def compare_backtests(
    payload: CompareRequest,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    return await build_comparison_response(
        db,
        payload.backtest_ids,
        current_workspace.id,
    )


@router.post(
    "/monte-carlo/{backtest_id}",
    response_model=MonteCarloResult,
    summary="Run Monte Carlo simulation",
    description=(
        "Bootstraps historical daily returns from a saved backtest to project a "
        "distribution of potential future equity paths."
    ),
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def monte_carlo(
    backtest_id: str,
    n_simulations: int = Query(1000, ge=100, le=10000),
    n_days: int = Query(252, ge=30, le=1260),
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    return await build_monte_carlo_response(
        db,
        backtest_id,
        current_workspace.id,
        n_simulations=n_simulations,
        n_days=n_days,
    )


@router.get(
    "/export/{backtest_id}",
    summary="Export a backtest as CSV",
    description=(
        "Exports configuration, performance metrics, equity curve, and monthly "
        "returns for a saved backtest in CSV format."
    ),
    responses={
        200: {
            "description": "CSV export stream.",
            "content": {
                "text/csv": {
                    "example": "=== Configuration ===\nstrategy,sma_crossover\n",
                }
            },
        },
        404: {"model": ErrorResponse, "description": "Backtest was not found."},
        501: {"model": ErrorResponse, "description": "Export format is unsupported."},
    },
)
async def export_results(
    backtest_id: str,
    format: str = Query("csv"),
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    if format != "csv":
        raise HTTPException(501, "Only CSV export is currently supported")

    csv_payload = await build_backtest_export(
        db,
        backtest_id,
        current_workspace.id,
    )
    return StreamingResponse(
        iter([csv_payload]),
        media_type="text/csv",
        headers={"Content-Disposition": (f"attachment; filename=backtest_{backtest_id[:8]}.csv")},
    )


@router.post(
    "/portfolio-blend",
    response_model=PortfolioBlendResponse,
    summary="Blend multiple backtests into a portfolio",
    description=(
        "Combines multiple saved backtests using custom or optimized weights and "
        "returns a portfolio-level equity curve, metrics, and contribution breakdown."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "At least two backtests are required.",
        },
        404: {
            "model": ErrorResponse,
            "description": "One of the requested backtests was not found.",
        },
    },
)
async def portfolio_blend(
    payload: PortfolioBlendRequest,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    return await build_portfolio_blend_response(
        db,
        payload.backtest_ids,
        current_workspace.id,
        weights_in=payload.weights,
        optimize=payload.optimize,
    )
