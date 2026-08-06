import logging
from collections.abc import AsyncGenerator

from app.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

# Async Engine for Read-Write operations (App logic, migrations, pinned charts)
engine_write = create_async_engine(
    settings.database_url_write,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Async Engine for Read-Only operations (Agent SQL tool execution)
engine_readonly = create_async_engine(
    settings.database_url_readonly,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

AsyncSessionWrite = async_sessionmaker(
    bind=engine_write,
    class_=AsyncSession,
    expire_on_commit=False
)

AsyncSessionReadonly = async_sessionmaker(
    bind=engine_readonly,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining read-write database session."""
    async with AsyncSessionWrite() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_readonly_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining read-only database session."""
    async with AsyncSessionReadonly() as session:
        try:
            yield session
        finally:
            await session.close()
