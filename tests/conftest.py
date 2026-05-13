"""Test fixtures — in-memory SQLite for fast isolated tests."""

import os
import pytest
import pytest_asyncio
from unittest.mock import patch
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

# Generate a test encryption key
TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()

# Set env vars BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["VAULT_ENCRYPTION_KEY"] = TEST_ENCRYPTION_KEY
os.environ["STRIPE_SECRET_KEY"] = ""
os.environ["STRIPE_WEBHOOK_SECRET"] = ""
os.environ["SENDGRID_API_KEY"] = ""
os.environ["ENVIRONMENT"] = "test"

from api.database import Base, get_db
from api.config import get_settings, Settings
from api.services.encryption import reset_fernet


@pytest_asyncio.fixture
async def db_engine():
    """Create an in-memory SQLite engine for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create a test database session."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    """Create a test HTTP client with database override."""
    # Reset fernet to pick up test key
    reset_fernet()

    from api.main import app

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
