from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from app.schemas.paper import PaperTradingSessionCreate
from app.services.paper_trading import PaperTradingManager

router = APIRouter(prefix="/paper", tags=["paper-trading"])


def get_paper_manager(request: Request) -> PaperTradingManager:
    manager = getattr(request.app.state, "paper_trading_manager", None)
    if manager is None:
        raise HTTPException(503, "Paper trading manager is not available")
    return manager


@router.get("/sessions")
async def list_paper_sessions(request: Request):
    manager = get_paper_manager(request)
    return await manager.list_sessions()


@router.post("/sessions")
async def create_paper_session(payload: PaperTradingSessionCreate, request: Request):
    manager = get_paper_manager(request)
    try:
        return await manager.create_session(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/sessions/{session_id}")
async def get_paper_session(session_id: str, request: Request):
    manager = get_paper_manager(request)
    try:
        return await manager.get_session_detail(session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/sessions/{session_id}/start")
async def start_paper_session(session_id: str, request: Request):
    manager = get_paper_manager(request)
    try:
        await manager.start_session(session_id)
        return await manager.get_session_detail(session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/sessions/{session_id}/pause")
async def pause_paper_session(session_id: str, request: Request):
    manager = get_paper_manager(request)
    try:
        await manager.pause_session(session_id)
        return await manager.get_session_detail(session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/sessions/{session_id}/stop")
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
