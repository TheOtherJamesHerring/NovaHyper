"""
app/api/v1/endpoints/auth.py
----------------------------
Login, token refresh, and logout endpoints.
"""
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.deps import CurrentUser, PlainDB
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models import User
from app.schemas import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services.audit import write_audit_event
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Obtain access + refresh tokens")
async def login(body: LoginRequest, request: Request, db: PlainDB) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == body.email, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        await write_audit_event(
            db=db,
            request=request,
            user=user,
            action="auth.login_failed",
            resource_type="auth",
            resource_id=None,
            payload={
                "tenant_id": user.tenant_id if user is not None else None,
                "user_id": user.id if user is not None else None,
                "action": "auth.login_failed",
                "resource_type": "auth",
                "resource_id": None,
            },
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Update last login timestamp
    user.last_login_at = datetime.now(UTC)
    await write_audit_event(
        db=db,
        request=request,
        user=user,
        action="auth.login",
        resource_type="auth",
        resource_id=user.id,
        payload={
            "tenant_id": user.tenant_id,
            "user_id": user.id,
            "action": "auth.login",
            "resource_type": "auth",
            "resource_id": user.id,
        },
    )
    await db.commit()

    claims = {
        "tenant_id": user.tenant_id,
        "role": user.role.value,
    }
    return TokenResponse(
        access_token=create_access_token(user.id, claims),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Exchange a refresh token for a new pair")
async def refresh_token(body: RefreshRequest, db: PlainDB) -> TokenResponse:
    from jose import JWTError
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")
        user_id: str = payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))  # noqa: E712
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    claims = {"tenant_id": user.tenant_id, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(user.id, claims),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse, summary="Current authenticated user")
async def me(user: CurrentUser) -> User:
    return user
