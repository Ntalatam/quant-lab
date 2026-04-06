from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.auth import RefreshTokenSession, User, Workspace, WorkspaceMembership
from app.models.backtest import BacktestRun
from app.models.custom_strategy import CustomStrategy
from app.models.paper import PaperTradingSession
from app.utils.datetime import utc_now_naive

PASSWORD_SALT_BYTES = 16
PASSWORD_HASH_BYTES = 64
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_BYTES = 48
JWT_HEADER = {"alg": "HS256", "typ": "JWT"}


class AuthError(ValueError):
    pass


@dataclass(frozen=True)
class AuthSessionBundle:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_session: RefreshTokenSession
    user: User
    workspace: Workspace
    membership: WorkspaceMembership


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _naive_utcnow() -> datetime:
    return utc_now_naive()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=PASSWORD_HASH_BYTES,
    )
    return "$".join(
        [
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _b64url_encode(salt),
            _b64url_encode(digest),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, n, r, p, salt_value, digest_value = password_hash.split("$", 5)
        if scheme != "scrypt":
            return False
        salt = _b64url_decode(salt_value)
        expected = _b64url_decode(digest_value)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except Exception:
        return False
    return hmac.compare_digest(actual, expected)


def _sign_bytes(value: bytes) -> str:
    signature = hmac.new(
        settings.AUTH_SECRET_KEY.encode("utf-8"),
        value,
        hashlib.sha256,
    ).digest()
    return _b64url_encode(signature)


def create_access_token(*, user: User) -> tuple[str, datetime]:
    issued_at = _utcnow()
    expires_at = issued_at + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_TTL_MINUTES)
    payload = {
        "sub": user.id,
        "email": user.email,
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded_header = _b64url_encode(_json_bytes(JWT_HEADER))
    encoded_payload = _b64url_encode(_json_bytes(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    return f"{encoded_header}.{encoded_payload}.{_sign_bytes(signing_input)}", expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_value, payload_value, signature_value = token.split(".", 2)
        signing_input = f"{header_value}.{payload_value}".encode("ascii")
        expected_signature = _sign_bytes(signing_input)
        if not hmac.compare_digest(signature_value, expected_signature):
            raise AuthError("Invalid token signature")
        header = json.loads(_b64url_decode(header_value))
        payload = json.loads(_b64url_decode(payload_value))
    except Exception as exc:
        raise AuthError("Invalid access token") from exc

    if header.get("alg") != "HS256" or payload.get("type") != ACCESS_TOKEN_TYPE:
        raise AuthError("Invalid access token")

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at <= int(_utcnow().timestamp()):
        raise AuthError("Access token expired")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _display_name_from_email(email: str) -> str:
    local_part = email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    if not local_part:
        return "QuantLab User"
    return " ".join(part.capitalize() for part in local_part.split())


def _workspace_name_for_user(user: User) -> str:
    base_name = user.display_name or _display_name_from_email(user.email)
    return f"{base_name} Personal"


def _client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def _client_user_agent(request: Request | None) -> str | None:
    if request is None:
        return None
    return request.headers.get("user-agent")


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    same_site = cast(
        Literal["lax", "strict", "none"] | None,
        settings.AUTH_COOKIE_SAMESITE,
    )
    response.set_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=same_site,
        max_age=settings.AUTH_REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        path="/api/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    same_site = cast(
        Literal["lax", "strict", "none"] | None,
        settings.AUTH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=same_site,
        path="/api/auth",
    )


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str | None,
) -> tuple[User, Workspace, WorkspaceMembership]:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise AuthError("An account with that email already exists")

    existing_users = int(await db.scalar(select(func.count()).select_from(User)) or 0)
    now = _naive_utcnow()
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name=f"{display_name or _display_name_from_email(email)} Personal",
        is_personal=True,
        personal_for_user_id=user.id,
        created_at=now,
        updated_at=now,
    )
    membership = WorkspaceMembership(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
        created_at=now,
    )

    db.add(user)
    db.add(workspace)
    db.add(membership)
    await db.flush()

    if existing_users == 0:
        await claim_legacy_resources(
            db,
            user_id=user.id,
            workspace_id=workspace.id,
        )

    return user, workspace, membership


async def claim_legacy_resources(db: AsyncSession, *, user_id: str, workspace_id: str) -> None:
    await db.execute(
        update(BacktestRun)
        .where(BacktestRun.workspace_id.is_(None))
        .values(workspace_id=workspace_id, created_by_user_id=user_id)
    )
    await db.execute(
        update(CustomStrategy)
        .where(CustomStrategy.workspace_id.is_(None))
        .values(workspace_id=workspace_id, created_by_user_id=user_id)
    )
    await db.execute(
        update(PaperTradingSession)
        .where(PaperTradingSession.workspace_id.is_(None))
        .values(workspace_id=workspace_id, created_by_user_id=user_id)
    )


async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    if not user.is_active:
        raise AuthError("This account is inactive")
    return user


async def get_user_personal_workspace(
    db: AsyncSession,
    *,
    user_id: str,
) -> tuple[Workspace, WorkspaceMembership]:
    result = await db.execute(
        select(Workspace, WorkspaceMembership)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(WorkspaceMembership.user_id == user_id)
        .order_by(Workspace.is_personal.desc(), Workspace.created_at.asc())
    )
    row = result.first()
    if row is None:
        raise AuthError("No workspace membership found for user")
    workspace, membership = row
    return workspace, membership


async def issue_session_tokens(
    db: AsyncSession,
    *,
    user: User,
    workspace: Workspace,
    membership: WorkspaceMembership,
    request: Request | None,
) -> AuthSessionBundle:
    access_token, access_expires_at = create_access_token(user=user)
    refresh_token = generate_refresh_token()
    now = _naive_utcnow()
    refresh_session = RefreshTokenSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=now + timedelta(days=settings.AUTH_REFRESH_TOKEN_TTL_DAYS),
        created_at=now,
        updated_at=now,
        last_used_at=now,
        user_agent=_client_user_agent(request),
        ip_address=_client_ip(request),
    )
    db.add(refresh_session)
    await db.flush()
    return AuthSessionBundle(
        access_token=access_token,
        access_expires_at=access_expires_at,
        refresh_token=refresh_token,
        refresh_session=refresh_session,
        user=user,
        workspace=workspace,
        membership=membership,
    )


async def rotate_refresh_session(
    db: AsyncSession,
    *,
    refresh_token: str,
    request: Request | None,
) -> tuple[RefreshTokenSession, User, str]:
    token_hash = hash_refresh_token(refresh_token)
    session = await db.scalar(
        select(RefreshTokenSession).where(RefreshTokenSession.token_hash == token_hash)
    )
    if session is None:
        raise AuthError("Refresh session not found")
    now = _naive_utcnow()
    if session.revoked_at is not None:
        raise AuthError("Refresh session has been revoked")
    if session.expires_at <= now:
        raise AuthError("Refresh session expired")

    user = await db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise AuthError("User not found or inactive")

    next_refresh_token = generate_refresh_token()
    session.token_hash = hash_refresh_token(next_refresh_token)
    session.last_used_at = now
    session.expires_at = now + timedelta(days=settings.AUTH_REFRESH_TOKEN_TTL_DAYS)
    session.user_agent = _client_user_agent(request)
    session.ip_address = _client_ip(request)
    await db.flush()

    return session, user, next_refresh_token


async def revoke_refresh_session(db: AsyncSession, *, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    token_hash = hash_refresh_token(refresh_token)
    session = await db.scalar(
        select(RefreshTokenSession).where(RefreshTokenSession.token_hash == token_hash)
    )
    if session is None or session.revoked_at is not None:
        return
    session.revoked_at = _naive_utcnow()
    await db.flush()


async def get_user_from_access_token(db: AsyncSession, *, token: str) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise AuthError("Invalid access token")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("User not found or inactive")
    return user


async def resolve_workspace_for_user(
    db: AsyncSession,
    *,
    user_id: str,
    workspace_id: str | None,
) -> tuple[Workspace, WorkspaceMembership]:
    query = (
        select(Workspace, WorkspaceMembership)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(WorkspaceMembership.user_id == user_id)
    )
    if workspace_id:
        query = query.where(Workspace.id == workspace_id)
    else:
        query = query.order_by(Workspace.is_personal.desc(), Workspace.created_at.asc())
    result = await db.execute(query)
    row = result.first()
    if row is None:
        raise AuthError("Workspace not found for user")
    workspace, membership = row
    return workspace, membership


def build_session_response(
    *,
    access_token: str,
    access_expires_at: datetime,
    user: User,
    workspace: Workspace,
    membership: WorkspaceMembership,
) -> dict[str, Any]:
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": access_expires_at,
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "created_at": user.created_at,
        },
        "workspace": {
            "id": workspace.id,
            "name": workspace.name,
            "is_personal": workspace.is_personal,
            "role": membership.role,
        },
    }


def build_current_session_response(
    *,
    user: User,
    workspace: Workspace,
    membership: WorkspaceMembership,
) -> dict[str, Any]:
    payload = build_session_response(
        access_token="",
        access_expires_at=_utcnow(),
        user=user,
        workspace=workspace,
        membership=membership,
    )
    payload.pop("access_token", None)
    payload.pop("token_type", None)
    payload.pop("expires_at", None)
    return payload


def get_refresh_token_from_request(request: Request) -> str | None:
    return request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)


def unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
