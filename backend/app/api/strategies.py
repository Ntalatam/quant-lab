"""
GET    /api/strategies/list                — List all built-in and custom strategies
GET    /api/strategies/{id}/params         — Get parameter schema for a strategy
GET    /api/strategies/custom/editor-spec  — Read the editor template and helper catalog
POST   /api/strategies/custom/validate     — Validate draft strategy code and extract params
GET    /api/strategies/custom              — List saved custom strategies
POST   /api/strategies/custom              — Save a new custom strategy
GET    /api/strategies/custom/{id}         — Read one saved custom strategy
PUT    /api/strategies/custom/{id}         — Update a saved custom strategy
DELETE /api/strategies/custom/{id}         — Delete a saved custom strategy
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_current_workspace
from app.database import get_db
from app.models.auth import User, Workspace
from app.schemas.common import ErrorResponse
from app.schemas.strategy import (
    CustomStrategyCreateRequest,
    CustomStrategyDetailResponse,
    CustomStrategySummaryResponse,
    CustomStrategyUpdateRequest,
    CustomStrategyValidateRequest,
    CustomStrategyValidateResponse,
    DeleteCustomStrategyResponse,
    StrategyEditorSpecResponse,
    StrategyInfoResponse,
    StrategyParamsResponse,
)
from app.services import cache
from app.services.custom_strategy import (
    CustomStrategyValidationError,
    create_custom_strategy,
    delete_custom_strategy,
    get_custom_strategy_record,
    get_editor_spec,
    list_custom_strategy_records,
    strategy_record_to_detail,
    strategy_record_to_summary,
    update_custom_strategy,
    validate_custom_strategy_source,
)
from app.services.strategy_registry import get_strategy_class, get_strategy_info, list_strategies

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get(
    "/list",
    response_model=list[StrategyInfoResponse],
    summary="List supported strategies",
    description=(
        "Returns both built-in and saved custom strategies, including parameter "
        "schemas, signal modes, and whether short-selling support is required."
    ),
)
async def get_strategies(
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    cache_key = f"strategies:list:{current_workspace.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    result = await list_strategies(db, workspace_id=current_workspace.id)
    cache.put(cache_key, result, ttl=300)
    return result


@router.get(
    "/custom/editor-spec",
    response_model=StrategyEditorSpecResponse,
    summary="Read the custom strategy editor contract",
    description=(
        "Returns the starter template, the safe helper catalog, and the guardrails "
        "that the browser-based strategy editor must respect."
    ),
)
async def get_custom_strategy_editor_spec():
    return get_editor_spec()


@router.post(
    "/custom/validate",
    response_model=CustomStrategyValidateResponse,
    summary="Validate draft custom strategy code",
    description=(
        "Parses a custom strategy draft, blocks unsafe syntax, extracts the "
        "parameter schema, and runs a dry-run validation against synthetic data."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "The custom strategy failed validation.",
        }
    },
)
async def validate_custom_strategy(payload: CustomStrategyValidateRequest):
    try:
        return validate_custom_strategy_source(payload.code)
    except CustomStrategyValidationError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "warnings": [],
            "preview": None,
            "extracted": None,
        }


@router.get(
    "/custom",
    response_model=list[CustomStrategySummaryResponse],
    summary="List saved custom strategies",
    description="Returns saved custom strategies for the in-browser strategy studio.",
)
async def list_custom_strategies(
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    strategies = await list_custom_strategy_records(db, workspace_id=current_workspace.id)
    return [strategy_record_to_summary(item) for item in strategies]


@router.post(
    "/custom",
    response_model=CustomStrategyDetailResponse,
    summary="Save a new custom strategy",
    description=(
        "Validates draft strategy code, persists it, and makes it available "
        "alongside built-in strategies in backtests and paper trading."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "The custom strategy failed validation.",
        }
    },
)
async def create_custom_strategy_route(
    payload: CustomStrategyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    try:
        strategy = await create_custom_strategy(
            db,
            payload.code,
            workspace_id=current_workspace.id,
            created_by_user_id=current_user.id,
        )
        await db.commit()
        await db.refresh(strategy)
    except CustomStrategyValidationError as exc:
        raise HTTPException(400, str(exc))

    cache.invalidate_prefix("strategies:")
    return strategy_record_to_detail(strategy)


@router.get(
    "/custom/{strategy_id}",
    response_model=CustomStrategyDetailResponse,
    summary="Read a saved custom strategy",
    responses={404: {"model": ErrorResponse, "description": "Strategy was not found."}},
)
async def get_custom_strategy_route(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    strategy = await get_custom_strategy_record(
        db,
        strategy_id,
        workspace_id=current_workspace.id,
    )
    if strategy is None:
        raise HTTPException(404, f"Custom strategy {strategy_id} not found")
    return strategy_record_to_detail(strategy)


@router.put(
    "/custom/{strategy_id}",
    response_model=CustomStrategyDetailResponse,
    summary="Update a saved custom strategy",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "The updated source code failed validation.",
        },
        404: {"model": ErrorResponse, "description": "Strategy was not found."},
    },
)
async def update_custom_strategy_route(
    strategy_id: str,
    payload: CustomStrategyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    strategy = await get_custom_strategy_record(
        db,
        strategy_id,
        workspace_id=current_workspace.id,
    )
    if strategy is None:
        raise HTTPException(404, f"Custom strategy {strategy_id} not found")
    try:
        strategy = await update_custom_strategy(db, strategy, payload.code)
        await db.commit()
        await db.refresh(strategy)
    except CustomStrategyValidationError as exc:
        raise HTTPException(400, str(exc))

    cache.invalidate_prefix("strategies:")
    return strategy_record_to_detail(strategy)


@router.delete(
    "/custom/{strategy_id}",
    response_model=DeleteCustomStrategyResponse,
    summary="Delete a saved custom strategy",
    responses={404: {"model": ErrorResponse, "description": "Strategy was not found."}},
)
async def delete_custom_strategy_route(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    strategy = await get_custom_strategy_record(
        db,
        strategy_id,
        workspace_id=current_workspace.id,
    )
    if strategy is None:
        raise HTTPException(404, f"Custom strategy {strategy_id} not found")
    await delete_custom_strategy(db, strategy)
    await db.commit()
    cache.invalidate_prefix("strategies:")
    return {"deleted": True, "id": strategy_id}


@router.get(
    "/{strategy_id}/params",
    response_model=StrategyParamsResponse,
    summary="Read the parameter schema for one strategy",
    description="Returns the full parameter schema and default values for the requested strategy.",
    responses={404: {"model": ErrorResponse, "description": "Strategy was not found."}},
)
async def get_strategy_params(
    strategy_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    try:
        cls = get_strategy_class(strategy_id)
        return {
            "id": strategy_id,
            "name": cls.name,
            "source_type": "builtin",
            "params": cls.param_schema,
            "defaults": cls.default_params,
        }
    except ValueError:
        pass

    try:
        strategy = await get_strategy_info(
            db,
            strategy_id,
            workspace_id=current_workspace.id,
        )
        return {
            "id": strategy["id"],
            "name": strategy["name"],
            "source_type": strategy["source_type"],
            "params": strategy["params"],
            "defaults": strategy["defaults"],
        }
    except ValueError:
        raise HTTPException(404, f"Strategy {strategy_id} not found")
