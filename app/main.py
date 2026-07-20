import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles

from app.core.logging import configure_logging
configure_logging()

from app.api.routers import (
    authRouter,
    userRouter,
    pagesRouter,
    courseRouter,
    sectionRouter,
    lessonRouter,
    stepRouter,
    fileRouter,
    enrollmentRouter,
    progressRouter,
    taskRouter,
    testCaseRouter,
    submissionRouter,
)
from app.core.database import engine
from app.core.redis import redis
from app.models import Base

@asynccontextmanager
async def lifespan(_app: FastAPI):
    await redis.ping()
    yield
    await engine.dispose()
    await redis.aclose()

app = FastAPI(lifespan=lifespan)

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="app/templates")

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

app.include_router(
    progressRouter,
    prefix='/api/progress',
    tags=['progress']
)

app.include_router(
    taskRouter,
    prefix='/api/tasks',
    tags=['tasks']
)

app.include_router(
    testCaseRouter,
    prefix='/api/test-cases',
    tags=['test-cases']
)

app.include_router(
    submissionRouter,
    prefix='/api/submissions',
    tags=['submissions']
)

app.include_router(pagesRouter)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
):
    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail
            }
        )
    if exc.status_code in (
        status.HTTP_404_NOT_FOUND,
        status.HTTP_403_FORBIDDEN
    ):
        return templates.TemplateResponse(
            request,
            name=f"errors/{exc.status_code}.html",
            status_code=exc.status_code
        )
    return await fastapi_http_exception_handler(request, exc)



@app.exception_handler(Exception)
async def exception_handler(
    request: Request,
    exc: Exception
):
    logger.exception(
        "Unhandled exception while processing %s:\n%s",
        request.url.path,
        exc
    )

    if request.url.path.startswith('/api/'):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal Server Error"
            }
        )
    return templates.TemplateResponse(
        request,
        name="errors/500.html",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
