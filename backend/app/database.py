import os
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DB_USER = os.getenv("POSTGRES_USER", "test")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "test")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5431")
DB_NAME = os.getenv("POSTGRES_DB", "localhost")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

AsyncSessionLocal: Callable[..., AsyncSession] = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
