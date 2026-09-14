"""Global pytest fixtures and test configuration with isolated in-memory database."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db_session
from app.core.config import Settings
from app.core.constants import AppEnvironment, LogFormat, LogLevel
from app.db.base import Base
from app.db.repositories.conversation import SQLAlchemyConversationRepository
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing isolated settings for testing."""
    return Settings(
        app_name="AI Chatbot Test",
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.DEBUG,
        log_format=LogFormat.CONSOLE,
        api_v1_prefix="/api/v1",
        database_url="sqlite+aiosqlite:///:memory:",
        chat_history_max_messages=50,
        rate_limit_per_minute=1000,
    )


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Fixture providing an isolated in-memory SQLite AsyncEngine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_db_session(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Fixture providing an isolated AsyncSession bound to the in-memory test database."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def test_repository(
    test_db_session: AsyncSession,
) -> SQLAlchemyConversationRepository:
    """Fixture providing an initialized SQLAlchemyConversationRepository."""
    return SQLAlchemyConversationRepository(session=test_db_session)


@pytest.fixture
def test_app(
    test_settings: Settings,
    test_db_session: AsyncSession,
) -> FastAPI:
    """Fixture providing a FastAPI test application instance with database dependency override."""
    app = create_app(settings=test_settings)

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return app


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Fixture providing an async HTTP test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
