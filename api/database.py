"""Database engine and session management."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from api.config import get_settings


class Base(DeclarativeBase):
    pass


def _normalize_async_url(url: str) -> str:
    """Railway provides `postgresql://` but SQLAlchemy async needs `postgresql+asyncpg://`."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def get_engine(url: str | None = None):
    db_url = _normalize_async_url(url or get_settings().database_url)
    return create_async_engine(db_url, echo=False, pool_pre_ping=True)


engine = None
SessionLocal = None


def init_db(url: str | None = None):
    global engine, SessionLocal
    engine = get_engine(url)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    if SessionLocal is None:
        init_db()
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
