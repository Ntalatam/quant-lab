from __future__ import annotations

from fastapi import Depends, Header, Request, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.auth import User, Workspace
from app.services.auth import (
    AuthError,
    get_user_from_access_token,
    resolve_workspace_for_user,
    unauthorized,
)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    token = (
        credentials.credentials
        if credentials is not None and credentials.scheme.lower() == "bearer"
        else request.query_params.get("access_token")
    )
    if not token:
        raise unauthorized()
    try:
        return await get_user_from_access_token(db, token=token)
    except AuthError as exc:
        raise unauthorized(str(exc)) from exc


async def get_current_workspace(
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workspace:
    try:
        workspace, _membership = await resolve_workspace_for_user(
            db,
            user_id=current_user.id,
            workspace_id=x_workspace_id,
        )
        return workspace
    except AuthError as exc:
        raise unauthorized(str(exc)) from exc


async def authenticate_websocket(
    websocket: WebSocket,
    db: AsyncSession,
) -> tuple[User, Workspace]:
    token = websocket.query_params.get("access_token")
    workspace_id = websocket.query_params.get("workspace_id")
    if not token:
        raise unauthorized()
    try:
        user = await get_user_from_access_token(db, token=token)
        workspace, _membership = await resolve_workspace_for_user(
            db,
            user_id=user.id,
            workspace_id=workspace_id,
        )
        return user, workspace
    except AuthError as exc:
        raise unauthorized(str(exc)) from exc
