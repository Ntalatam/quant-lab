from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_current_workspace
from app.database import get_db
from app.models.auth import User, Workspace
from app.schemas.auth import (
    AuthSessionResponse,
    CurrentSessionResponse,
    LoginRequest,
    RegisterRequest,
)
from app.schemas.common import ErrorResponse, StatusMessageResponse
from app.services.auth import (
    AuthError,
    authenticate_user,
    build_current_session_response,
    build_session_response,
    clear_refresh_cookie,
    get_refresh_token_from_request,
    get_user_personal_workspace,
    issue_session_tokens,
    register_user,
    revoke_refresh_session,
    rotate_refresh_session,
    set_refresh_cookie,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthSessionResponse,
    summary="Register a new user",
    responses={400: {"model": ErrorResponse}},
)
async def register(
    payload: RegisterRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        user, workspace, membership = await register_user(
            db,
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
        bundle = await issue_session_tokens(
            db,
            user=user,
            workspace=workspace,
            membership=membership,
            request=request,
        )
        await db.commit()
    except AuthError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    set_refresh_cookie(response, bundle.refresh_token)
    return build_session_response(
        access_token=bundle.access_token,
        access_expires_at=bundle.access_expires_at,
        user=user,
        workspace=workspace,
        membership=membership,
    )


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    summary="Authenticate a user",
    responses={401: {"model": ErrorResponse}},
)
async def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await authenticate_user(db, email=payload.email, password=payload.password)
        workspace, membership = await get_user_personal_workspace(db, user_id=user.id)
        bundle = await issue_session_tokens(
            db,
            user=user,
            workspace=workspace,
            membership=membership,
            request=request,
        )
        await db.commit()
    except AuthError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    set_refresh_cookie(response, bundle.refresh_token)
    return build_session_response(
        access_token=bundle.access_token,
        access_expires_at=bundle.access_expires_at,
        user=user,
        workspace=workspace,
        membership=membership,
    )


@router.post(
    "/refresh",
    response_model=AuthSessionResponse,
    summary="Rotate a refresh token and issue a new access token",
    responses={401: {"model": ErrorResponse}},
)
async def refresh_session(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = get_refresh_token_from_request(request)
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token missing")

    try:
        _refresh_session_row, user, next_refresh_token = await rotate_refresh_session(
            db,
            refresh_token=refresh_token,
            request=request,
        )
        workspace, membership = await get_user_personal_workspace(db, user_id=user.id)
        from app.services.auth import create_access_token

        access_token, access_expires_at = create_access_token(user=user)
    except AuthError as exc:
        await db.rollback()
        clear_refresh_cookie(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    await db.commit()
    set_refresh_cookie(response, next_refresh_token)
    return build_session_response(
        access_token=access_token,
        access_expires_at=access_expires_at,
        user=user,
        workspace=workspace,
        membership=membership,
    )


@router.post(
    "/logout",
    response_model=StatusMessageResponse,
    summary="Revoke the current refresh session",
)
async def logout(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await revoke_refresh_session(db, refresh_token=get_refresh_token_from_request(request))
    await db.commit()
    clear_refresh_cookie(response)
    return {"status": "ok", "message": "Logged out"}


@router.get(
    "/me",
    response_model=CurrentSessionResponse,
    summary="Return the current authenticated user and workspace",
    responses={401: {"model": ErrorResponse}},
)
async def me(
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
):
    from app.services.auth import resolve_workspace_for_user

    _workspace, membership = await resolve_workspace_for_user(
        db,
        user_id=current_user.id,
        workspace_id=current_workspace.id,
    )
    return build_current_session_response(
        user=current_user,
        workspace=_workspace,
        membership=membership,
    )
