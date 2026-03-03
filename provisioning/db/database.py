"""Database connection and session management."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# Database URL from environment (default: local PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://clawgeeks:clawgeeks@localhost:5432/clawgeeks"
)

# Create async engine with appropriate settings for database type
if DATABASE_URL.startswith("sqlite"):
    # SQLite: use StaticPool for in-memory databases, no pool_size
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL/other: use connection pooling
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
        pool_size=5,
        max_overflow=10,
    )

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize database (create tables)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI: yields database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def DatabaseSession() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for standalone database access."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
