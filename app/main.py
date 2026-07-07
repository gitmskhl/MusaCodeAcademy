from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routers import (
    authRouter,
    userRouter,
    pagesRouter,
    courseRouter,
    sectionRouter,
    lessonRouter,
    stepRouter,
    fileRouter,
    enrollmentRouter
)
from app.core.database import engine
from app.models import Base

@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)



app.include_router(
    authRouter,
    prefix="/api/auth",
    tags=["auth"]
)

app.include_router(
    userRouter,
    prefix="/api/users",
    tags=["user"]
)

app.include_router(
    courseRouter,
    prefix='/api/courses',
    tags=['course']
)

app.include_router(
    sectionRouter,
    prefix='/api/sections',
    tags=['section']
)

app.include_router(
    lessonRouter,
    prefix='/api/lessons',
    tags=['lesson']
)

app.include_router(
    stepRouter,
    prefix='/api/steps',
    tags=['step']
)

app.include_router(
    fileRouter,
    prefix='/api/files',
    tags=['file']
)

app.include_router(
    enrollmentRouter,
    prefix='/api/enrollments',
    tags=['enrollment']
)

app.include_router(pagesRouter)