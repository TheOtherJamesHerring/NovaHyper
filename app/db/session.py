"""
app/db/session.py
-----------------
Async SQLAlchemy engine + session factory.

TENANT ISOLATION
Every database session must have the current tenant's UUID injected
as a PostgreSQL session variable before any query runs:

    SET LOCAL app.tenant_id = '<uuid>';

This activates the Row-Level Security policies defined on every tenant-scoped
table.  The ``tenant_session`` context manager handles this automatically.
Never run tenant-scoped queries on a plain ``AsyncSession``.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.sql import text

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DB_ECHO,
    # Return connections to the pool after each transaction — important for
    # RLS because SET LOCAL is scoped to a transaction, not a connection.
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Plain unauthenticated session — for internal/admin operations only.
    FastAPI dependency: ``db: AsyncSession = Depends(get_db)``
    """
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def tenant_session(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Session with tenant RLS activated.  Always use this for any operation
    that touches tenant-scoped tables (vms, disks, backups, etc.).

    Usage::

        async with tenant_session(tenant_id) as db:
            result = await db.execute(select(VM))
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Activate RLS for this transaction only (SET LOCAL is safe with
            # the connection pool because it reverts on transaction end).
            await session.execute(
                text(f"SET LOCAL app.tenant_id = '{tenant_id}'")
            )
            yield session
