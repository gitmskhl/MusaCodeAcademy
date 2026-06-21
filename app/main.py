from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routers import authRouter
from app.core.database import engine
from app.models import Base


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.include_router(
    authRouter,
    prefix='/api/auth',
    tags=['auth']
)
