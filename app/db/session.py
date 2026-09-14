"""Async SQLAlchemy engine, session maker, and connectivity validation."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.db.exceptions import PersistenceConfigurationError

logger = logging.getLogger("app.db.session")


def create_async_engine_instance(database_url: str) -> AsyncEngine:
    """Create an AsyncEngine instance with appropriate connection pool settings."""
    if not database_url:
        raise PersistenceConfigurationError("DATABASE_URL must not be empty.")

    engine_kwargs: dict[str, bool] = {
        "echo": False,
    }

    # SQLite specific connection settings
    if "sqlite" in database_url:
        # SQLite with aiosqlite requires disabling check_same_thread if multithreaded
        engine_kwargs["connect_args"] = {"check_same_thread": False}  # type: ignore[assignment]

    try:
        engine = create_async_engine(database_url, **engine_kwargs)
        return engine
    except Exception as exc:
        logger.error("Failed to construct SQLAlchemy async engine: %s", exc)
        raise PersistenceConfigurationError(f"Could not construct database engine: {exc}") from exc


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def check_database_connection(session_factory: async_sessionmaker[AsyncSession]) -> bool:
    """Execute a lightweight SQL probe to verify database connectivity."""
    try:
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            scalar = result.scalar()
            return scalar == 1
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        return False


# Module-level engine and session factory caches
_cached_engine: AsyncEngine | None = None
_cached_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Retrieve or initialize the singleton AsyncEngine."""
    global _cached_engine
    if _cached_engine is None:
        app_settings = settings or get_settings()
        _cached_engine = create_async_engine_instance(app_settings.database_url)
    return _cached_engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Retrieve or initialize the singleton async_sessionmaker."""
    global _cached_session_factory
    if _cached_session_factory is None:
        engine = get_engine(settings)
        _cached_session_factory = create_session_factory(engine)
    return _cached_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an isolated async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
