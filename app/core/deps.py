"""
app/core/deps.py
----------------
FastAPI dependency injection.

Every protected endpoint gets the current user injected via ``CurrentUser``.
Tenant-scoped endpoints get ``TenantDB`` — a session with RLS activated.

Usage in endpoints::

    @router.get("/vms")
    async def list_vms(
        db: TenantDB,
        user: CurrentUser,
    ) -> list[VMResponse]:
        ...
"""
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal, tenant_session
from app.models import User, UserRole

_bearer = HTTPBearer(auto_error=True)


async def _get_db() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        yield session


async def _get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
    db: AsyncSession = Depends(_get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))  # noqa: E712
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def _get_tenant_db(user: User = Depends(_get_current_user)) -> AsyncSession:  # type: ignore[return]
    async with tenant_session(user.tenant_id) as db:
        yield db


# ── Public type aliases (import these in endpoints) ────────────────────────────

CurrentUser = Annotated[User, Depends(_get_current_user)]
TenantDB    = Annotated[AsyncSession, Depends(_get_tenant_db)]
PlainDB     = Annotated[AsyncSession, Depends(_get_db)]


# ── Role guards ────────────────────────────────────────────────────────────────

def require_roles(*roles: UserRole):
    """
    Dependency factory that raises 403 if the current user's role is not in
    the allowed set.

    Usage::

        @router.delete("/vms/{vm_id}", dependencies=[Depends(require_roles(UserRole.tenant_admin))])
    """
    async def _check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return Depends(_check)


MSPAdminOnly   = require_roles(UserRole.msp_admin)
TenantAdminUp  = require_roles(UserRole.msp_admin, UserRole.tenant_admin)
OperatorUp     = require_roles(UserRole.msp_admin, UserRole.tenant_admin, UserRole.operator)
