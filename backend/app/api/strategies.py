"""
GET /api/strategies/list           — List all available strategies
GET /api/strategies/{id}/params    — Get parameter schema for a strategy
"""

from fastapi import APIRouter, HTTPException

from app.schemas.common import ErrorResponse
from app.schemas.strategy import StrategyInfoResponse, StrategyParamsResponse
from app.services.strategy_registry import get_strategy_class, list_strategies

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get(
    "/list",
    response_model=list[StrategyInfoResponse],
    summary="List supported strategies",
    description=(
        "Returns strategy metadata, parameter schemas, signal modes, and whether "
        "the strategy requires short-selling support."
    ),
)
async def get_strategies():
    return list_strategies()


@router.get(
    "/{strategy_id}/params",
    response_model=StrategyParamsResponse,
    summary="Read the parameter schema for one strategy",
    description="Returns the full parameter schema and default values for the requested strategy.",
    responses={404: {"model": ErrorResponse, "description": "Strategy was not found."}},
)
async def get_strategy_params(strategy_id: str):
    try:
        cls = get_strategy_class(strategy_id)
        return {
            "id": strategy_id,
            "name": cls.name,
            "params": cls.param_schema,
            "defaults": cls.default_params,
        }
    except ValueError:
        raise HTTPException(404, f"Strategy {strategy_id} not found")
