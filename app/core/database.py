from collections.abc import AsyncGenerator
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

database_url = make_url(settings.sqlalchemy_database_url)

engine_kwargs = {}

if database_url.drivername.startswith('sqlite'):
    engine_kwargs['connect_args'] = {"check_same_thread": False}

engine = create_async_engine(
    url=settings.sqlalchemy_database_url,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        