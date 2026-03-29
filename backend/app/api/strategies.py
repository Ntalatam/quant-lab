"""
GET /api/strategies/list           — List all available strategies
GET /api/strategies/{id}/params    — Get parameter schema for a strategy
"""

from fastapi import APIRouter, HTTPException

from app.services.strategy_registry import list_strategies, get_strategy_class

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("/list")
async def get_strategies():
    return list_strategies()


@router.get("/{strategy_id}/params")
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
