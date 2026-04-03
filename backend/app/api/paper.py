from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from app.schemas.common import ErrorResponse
from app.schemas.paper import (
    PaperTradingSessionCreate,
    PaperTradingSessionDetail,
    PaperTradingSessionSummary,
)
from app.services.paper_trading import PaperTradingManager

router = APIRouter(prefix="/paper", tags=["paper-trading"])


def get_paper_manager(request: Request) -> PaperTradingManager:
    manager = getattr(request.app.state, "paper_trading_manager", None)
    if manager is None:
        raise HTTPException(503, "Paper trading manager is not available")
    return manager


@router.get(
    "/sessions",
    response_model=list[PaperTradingSessionSummary],
    summary="List paper-trading sessions",
    description="Returns every persisted paper-trading session with summary performance and runtime state.",
    responses={503: {"model": ErrorResponse, "description": "Paper-trading runtime unavailable."}},
)
async def list_paper_sessions(request: Request):
    manager = get_paper_manager(request)
    return await manager.list_sessions()


@router.post(
    "/sessions",
    response_model=PaperTradingSessionDetail,
    summary="Create a paper-trading session",
    description=(
        "Creates a new paper-trading session with strategy, execution, and risk "
        "settings. The session can optionally start immediately."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Session configuration was invalid."},
        503: {"model": ErrorResponse, "description": "Paper-trading runtime unavailable."},
    },
)
async def create_paper_session(payload: PaperTradingSessionCreate, request: Request):
    manager = get_paper_manager(request)
    try:
        return await manager.create_session(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get(
    "/sessions/{session_id}",
    response_model=PaperTradingSessionDetail,
    summary="Get one paper-trading session",
    description="Returns the live state, positions, recent events, and equity curve for a paper session.",
    responses={
        404: {"model": ErrorResponse, "description": "Session was not found."},
        503: {"model": ErrorResponse, "description": "Paper-trading runtime unavailable."},
    },
)
async def get_paper_session(session_id: str, request: Request):
    manager = get_paper_manager(request)
    try:
        return await manager.get_session_detail(session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post(
    "/sessions/{session_id}/start",
    response_model=PaperTradingSessionDetail,
    summary="Start a paper session",
    description="Transitions a paper-trading session into the active polling and execution state.",
    responses={
        404: {"model": ErrorResponse, "description": "Session was not found."},
        503: {"model": ErrorResponse, "description": "Paper-trading runtime unavailable."},
    },
)
async def start_paper_session(session_id: str, request: Request):
    manager = get_paper_manager(request)
    try:
        await manager.start_session(session_id)
        return await manager.get_session_detail(session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post(
    "/sessions/{session_id}/pause",
    response_model=PaperTradingSessionDetail,
    summary="Pause a paper session",
    description="Stops polling and order generation while leaving the paper session intact.",
    responses={
        404: {"model": ErrorResponse, "description": "Session was not found."},
        503: {"model": ErrorResponse, "description": "Paper-trading runtime unavailable."},
    },
)
async def pause_paper_session(session_id: str, request: Request):
    manager = get_paper_manager(request)
    try:
        await manager.pause_session(session_id)
        return await manager.get_session_detail(session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post(
    "/sessions/{session_id}/stop",
    response_model=PaperTradingSessionDetail,
    summary="Stop a paper session",
    description="Stops the session and finalizes its status without deleting its audit trail.",
    responses={
        404: {"model": ErrorResponse, "description": "Session was not found."},
        503: {"model": ErrorResponse, "description": "Paper-trading runtime unavailable."},
    },
)
async def stop_paper_session(session_id: str, request: Request):
    manager = get_paper_manager(request)
    try:
        await manager.stop_session(session_id)
        return await manager.get_session_detail(session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.websocket("/sessions/{session_id}/ws")
async def paper_session_websocket(websocket: WebSocket, session_id: str):
    manager = getattr(websocket.app.state, "paper_trading_manager", None)
    await websocket.accept()
    if manager is None:
        await websocket.send_json(
            {"type": "error", "message": "Paper trading manager is not available"}
        )
        await websocket.close()
        return

    try:
        detail = await manager.get_session_detail(session_id)
        await websocket.send_json(
            {"type": "snapshot", "session": jsonable_encoder(detail)}
        )
        await manager.subscribe(session_id, websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except ValueError as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        await manager.unsubscribe(session_id, websocket)
