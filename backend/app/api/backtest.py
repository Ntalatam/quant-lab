"""
Backtest API endpoints.

POST   /api/backtest/run      — Run a new backtest
GET    /api/backtest/list      — List all past backtests (summary)
GET    /api/backtest/{id}      — Get full backtest result
DELETE /api/backtest/{id}      — Delete a backtest
POST   /api/backtest/sweep     — Parameter sensitivity sweep
"""

import json
import time

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import authenticate_websocket, get_current_user, get_current_workspace
from app.database import get_db
from app.models.auth import User, Workspace
from app.models.backtest import BacktestRun
from app.models.trade import TradeRecord
from app.observability import elapsed_ms, get_logger
from app.schemas.backtest import (
    BacktestConfig,
    BacktestListResponse,
    BacktestResultResponse,
    BacktestSweep2DConfig,
    BacktestSweepConfig,
    BayesOptConfig,
    LineageResponse,
    LineageTagRequest,
    LineageTagResponse,
    NotesUpdateRequest,
    NotesUpdateResponse,
    WalkForwardRequest,
)
from app.schemas.common import DeleteResponse, ErrorResponse
from app.schemas.jobs import ResearchJobResponse
from app.services.backtest_engine import run_backtest
from app.services.backtest_runs import (
    load_backtest_detail,
    persist_backtest_result,
    serialize_backtest_run,
)
from app.services.jobs import enqueue_research_job, serialize_job

router = APIRouter(prefix="/backtest", tags=["backtest"])
logger = get_logger(__name__)


@router.post(
    "/run",
    response_model=ResearchJobResponse,
    status_code=202,
    summary="Queue a backtest run",
    description=(
        "Queues a full historical simulation for the background worker and returns "
        "the persisted job record used for status polling."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Backtest configuration was invalid.",
        },
        500: {
            "model": ErrorResponse,
            "description": "Backtest execution failed unexpectedly.",
        },
    },
)
async def execute_backtest(
    config: BacktestConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    start_time = time.perf_counter()
    log = logger.bind(
        strategy_id=config.strategy_id,
        tickers=config.tickers,
        benchmark=config.benchmark,
    )
    job = await enqueue_research_job(
        db,
        kind="backtest_run",
        request_payload=config.model_dump(),
        workspace_id=current_workspace.id,
        created_by_user_id=current_user.id,
        progress_message="Queued backtest run.",
    )
    log.info(
        "backtest.job_queued",
        duration_ms=elapsed_ms(start_time),
        job_id=job.id,
    )
    return serialize_job(job)


@router.get(
    "/list",
    response_model=BacktestListResponse,
    summary="List saved backtests",
    description="Returns paginated saved backtests with summary performance metrics for result-table views.",
)
async def list_backtests(
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    from sqlalchemy import func

    total = await db.scalar(
        select(func.count())
        .select_from(BacktestRun)
        .where(BacktestRun.workspace_id == current_workspace.id)
    )
    result = await db.execute(
        select(BacktestRun)
        .where(BacktestRun.workspace_id == current_workspace.id)
        .order_by(BacktestRun.created_at.desc(), BacktestRun.id.desc())
        .limit(limit)
        .offset(offset)
    )
    runs = result.scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "strategy_name": r.strategy_id,
                "tickers": r.tickers,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "total_return_pct": r.metrics.get("total_return_pct", 0),
                "sharpe_ratio": r.metrics.get("sharpe_ratio", 0),
                "max_drawdown_pct": r.metrics.get("max_drawdown_pct", 0),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "lineage_tag": r.lineage_tag,
                "version": r.version,
            }
            for r in runs
        ],
        "total": total or 0,
    }


@router.get(
    "/{backtest_id}",
    response_model=BacktestResultResponse,
    summary="Read a saved backtest",
    description="Returns the persisted run configuration, analytics series, trade log, and notes for one backtest.",
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def get_backtest(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    detail = await load_backtest_detail(
        db,
        backtest_id,
        workspace_id=current_workspace.id,
    )
    if detail is None:
        raise HTTPException(404, "Backtest not found")
    run, trades = detail
    return serialize_backtest_run(run, trades)


@router.delete(
    "/{backtest_id}",
    response_model=DeleteResponse,
    summary="Delete a saved backtest",
    description="Deletes the saved backtest record and its persisted trade ledger.",
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def delete_backtest(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(
        select(BacktestRun).where(
            BacktestRun.id == backtest_id,
            BacktestRun.workspace_id == current_workspace.id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    await db.execute(delete(TradeRecord).where(TradeRecord.backtest_run_id == backtest_id))
    await db.execute(delete(BacktestRun).where(BacktestRun.id == backtest_id))
    await db.commit()
    return {"status": "deleted"}


@router.patch(
    "/{backtest_id}/notes",
    response_model=NotesUpdateResponse,
    summary="Update analyst notes for a backtest",
    description="Stores free-form notes used to annotate a saved backtest result.",
    responses={404: {"model": ErrorResponse, "description": "Backtest was not found."}},
)
async def update_notes(
    backtest_id: str,
    payload: NotesUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(
        select(BacktestRun).where(
            BacktestRun.id == backtest_id,
            BacktestRun.workspace_id == current_workspace.id,
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")
    run.notes = payload.notes[:2000]
    await db.commit()
    return {"id": backtest_id, "notes": run.notes}


@router.post(
    "/sweep",
    response_model=ResearchJobResponse,
    status_code=202,
    summary="Queue a one-dimensional parameter sweep",
    description=(
        "Runs the same base configuration multiple times while varying a single "
        "parameter and returns summary metrics for each value."
    ),
    responses={400: {"model": ErrorResponse, "description": "Sweep request was invalid."}},
)
async def parameter_sweep(
    config: BacktestSweepConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    job = await enqueue_research_job(
        db,
        kind="backtest_sweep",
        request_payload=config.model_dump(),
        workspace_id=current_workspace.id,
        created_by_user_id=current_user.id,
        progress_message="Queued parameter sweep.",
    )
    return serialize_job(job)


@router.post(
    "/sweep2d",
    response_model=ResearchJobResponse,
    status_code=202,
    summary="Queue a two-dimensional parameter sweep",
    description=(
        "Evaluates a backtest across a 2D grid of parameter combinations and "
        "returns a heatmap-ready response."
    ),
    responses={400: {"model": ErrorResponse, "description": "Sweep request was invalid."}},
)
async def parameter_sweep_2d(
    config: BacktestSweep2DConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    job = await enqueue_research_job(
        db,
        kind="backtest_sweep2d",
        request_payload=config.model_dump(),
        workspace_id=current_workspace.id,
        created_by_user_id=current_user.id,
        progress_message="Queued 2D parameter sweep.",
    )
    return serialize_job(job)


@router.post(
    "/walk-forward",
    response_model=ResearchJobResponse,
    status_code=202,
    summary="Queue walk-forward analysis",
    description=(
        "Splits a strategy into rolling in-sample and out-of-sample windows to "
        "measure robustness and out-of-sample degradation."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Walk-forward request was invalid.",
        },
        500: {"model": ErrorResponse, "description": "Walk-forward execution failed."},
    },
)
async def walk_forward(
    payload: WalkForwardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    job = await enqueue_research_job(
        db,
        kind="backtest_walk_forward",
        request_payload=payload.model_dump(),
        workspace_id=current_workspace.id,
        created_by_user_id=current_user.id,
        progress_message="Queued walk-forward analysis.",
    )
    return serialize_job(job)


@router.post(
    "/optimize",
    response_model=ResearchJobResponse,
    status_code=202,
    summary="Queue Bayesian parameter optimization",
    description=(
        "Uses Optuna to evaluate full backtests across parameter ranges and "
        "returns the best parameter set plus the complete trial log."
    ),
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Optimization request was invalid.",
        },
        500: {
            "model": ErrorResponse,
            "description": "Optimization could not be completed.",
        },
    },
)
async def bayesian_optimize(
    config: BayesOptConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    job = await enqueue_research_job(
        db,
        kind="backtest_optimize",
        request_payload=config.model_dump(),
        workspace_id=current_workspace.id,
        created_by_user_id=current_user.id,
        progress_message="Queued Bayesian optimization.",
    )
    return serialize_job(job)


# ── Versioning / lineage ──────────────────────────────────────────────────


@router.patch(
    "/{backtest_id}/lineage",
    response_model=LineageTagResponse,
    summary="Tag a backtest with a lineage identifier",
    description=(
        "Assigns a lineage tag and optional parent link. "
        "The version number is auto-incremented within the lineage."
    ),
    responses={404: {"model": ErrorResponse}},
)
async def set_lineage(
    backtest_id: str,
    payload: LineageTagRequest,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    r = await db.execute(
        select(BacktestRun).where(
            BacktestRun.id == backtest_id,
            BacktestRun.workspace_id == current_workspace.id,
        )
    )
    run = r.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Backtest not found")

    # Compute next version in this lineage
    existing = await db.execute(
        select(BacktestRun.version)
        .where(
            BacktestRun.lineage_tag == payload.lineage_tag,
            BacktestRun.workspace_id == current_workspace.id,
        )
        .order_by(BacktestRun.version.desc())
    )
    max_ver = existing.scalar()
    next_ver = (max_ver or 0) + 1

    run.lineage_tag = payload.lineage_tag
    run.version = next_ver
    run.parent_id = payload.parent_id
    await db.commit()

    return {
        "id": run.id,
        "lineage_tag": run.lineage_tag,
        "version": run.version,
        "parent_id": run.parent_id,
    }


@router.get(
    "/lineage/{tag}",
    response_model=LineageResponse,
    summary="Get full lineage for a tag",
    description=(
        "Returns all backtests tagged with the given lineage, ordered by version, "
        "with parameter diffs showing what changed between iterations."
    ),
    responses={404: {"model": ErrorResponse}},
)
async def get_lineage(
    tag: str,
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    result = await db.execute(
        select(BacktestRun)
        .where(
            BacktestRun.lineage_tag == tag,
            BacktestRun.workspace_id == current_workspace.id,
        )
        .order_by(BacktestRun.version.asc())
    )
    runs = result.scalars().all()

    if not runs:
        raise HTTPException(404, f"No backtests found for lineage '{tag}'")

    entries = []
    prev_params: dict | None = None
    for run in runs:
        params = run.strategy_params or {}
        diffs = []
        if prev_params is not None:
            all_keys = set(list(prev_params.keys()) + list(params.keys()))
            for k in sorted(all_keys):
                old = prev_params.get(k)
                new = params.get(k)
                if old != new:
                    diffs.append({"key": k, "old_value": old, "new_value": new})

        entries.append(
            {
                "id": run.id,
                "version": run.version,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "notes": run.notes or "",
                "strategy_id": run.strategy_id,
                "tickers": run.tickers,
                "params": params,
                "sharpe_ratio": run.metrics.get("sharpe_ratio", 0),
                "total_return_pct": run.metrics.get("total_return_pct", 0),
                "max_drawdown_pct": run.metrics.get("max_drawdown_pct", 0),
                "param_diffs": diffs,
            }
        )
        prev_params = params

    return {"lineage_tag": tag, "entries": entries}


@router.get(
    "/lineages",
    summary="List all lineage tags",
    description="Returns all distinct lineage tags and how many versions each has.",
)
async def list_lineages(
    db: AsyncSession = Depends(get_db),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    from sqlalchemy import func

    result = await db.execute(
        select(
            BacktestRun.lineage_tag,
            func.count(BacktestRun.id).label("count"),
            func.max(BacktestRun.version).label("max_version"),
        )
        .where(
            BacktestRun.lineage_tag.isnot(None),
            BacktestRun.workspace_id == current_workspace.id,
        )
        .group_by(BacktestRun.lineage_tag)
        .order_by(func.max(BacktestRun.created_at).desc())
    )
    rows = result.all()
    return {
        "lineages": [
            {"tag": row.lineage_tag, "count": row.count, "max_version": row.max_version}
            for row in rows
        ]
    }


@router.websocket("/ws")
async def backtest_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time backtest progress streaming.

    Protocol:
      Client → sends JSON BacktestConfig
      Server → streams {"type":"progress","bar":N,"total":M,"date":"...","equity":V,"pct":0..1}
      Server → sends   {"type":"complete","id":"...","result":{...}} on success
      Server → sends   {"type":"error","message":"..."} on failure
    """
    from app.database import async_session

    await websocket.accept()
    try:
        async with async_session() as auth_db:
            current_user, current_workspace = await authenticate_websocket(websocket, auth_db)

        raw = await websocket.receive_text()
        try:
            config_data = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "message": "Invalid JSON payload"})
            return

        try:
            config = BacktestConfig(**config_data)
        except ValidationError:
            await websocket.send_json({"type": "error", "message": "Invalid backtest config"})
            return

        async def on_progress(bar_num: int, total_bars: int, date_str: str, equity: float):
            pct = round(bar_num / total_bars, 4) if total_bars else 0
            try:
                await websocket.send_json(
                    {
                        "type": "progress",
                        "bar": bar_num,
                        "total": total_bars,
                        "date": date_str,
                        "equity": round(equity, 2),
                        "pct": pct,
                    }
                )
            except Exception:
                pass  # client disconnected mid-run

        async with async_session() as db:
            try:
                result = await run_backtest(
                    db,
                    config,
                    on_progress=on_progress,
                    workspace_id=current_workspace.id,
                )
                await persist_backtest_result(
                    db,
                    config,
                    result,
                    workspace_id=current_workspace.id,
                    created_by_user_id=current_user.id,
                )

                await websocket.send_json({"type": "complete", "id": result["id"]})
            except ValueError as e:
                logger.warning("backtest.websocket_rejected", error=str(e))
                await websocket.send_json({"type": "error", "message": str(e)})
            except Exception as e:
                logger.exception("backtest.websocket_failed", error=str(e))
                await websocket.send_json({"type": "error", "message": f"Backtest failed: {e}"})

    except WebSocketDisconnect:
        logger.debug("backtest.websocket_disconnected")
    except Exception as e:
        logger.exception("backtest.websocket_protocol_failed", error=str(e))
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
