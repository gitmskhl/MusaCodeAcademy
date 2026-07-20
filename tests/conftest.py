import os
from io import BytesIO
from uuid import uuid4

import asyncpg
from httpx import AsyncClient, ASGITransport
import pytest
import pytest_asyncio
from fastapi import UploadFile
from starlette.datastructures import Headers
from sqlalchemy import make_url, select, text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import get_db
from app.enums import UserRole
from app.models import Base, Course, User, Section
from app.main import app
from app.core.config import settings
from app.services.storage import StorageService


def _quote_identifier(identifier: str) -> str:
    escaped_identifier = identifier.replace('"', '""')
    return f'"{escaped_identifier}"'


def _make_test_database_url() -> str:
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if test_database_url:
        return test_database_url

    database_url = make_url(settings.sqlalchemy_database_url)
    database_name = database_url.database
    if not database_name:
        raise RuntimeError("SQLALCHEMY_DATABASE_URL must include a database name")

    if not database_name.endswith("_test"):
        database_url = database_url.set(database=f"{database_name}_test")

    return database_url.render_as_string(hide_password=False)


TEST_DATABASE_URL = _make_test_database_url()
TEST_DATABASE_NAME = make_url(TEST_DATABASE_URL).database

if not TEST_DATABASE_NAME or not TEST_DATABASE_NAME.endswith("_test"):
    raise RuntimeError(
        "Test database name must end with '_test'. "
        "Set TEST_DATABASE_URL to a dedicated PostgreSQL test database."
    )

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

test_async_session_maker = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False,
    class_=AsyncSession
)


async def _ensure_test_database_exists() -> None:
    database_url = make_url(TEST_DATABASE_URL)
    if not database_url.drivername.startswith("postgresql"):
        return

    connection = await asyncpg.connect(
        user=database_url.username,
        password=database_url.password,
        host=database_url.host or "localhost",
        port=database_url.port or 5432,
        database=os.getenv("TEST_MAINTENANCE_DATABASE", "postgres"),
    )
    try:
        exists = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_url.database,
        )
        if not exists:
            await connection.execute(
                f"CREATE DATABASE {_quote_identifier(database_url.database)}"
            )
    finally:
        await connection.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    await _ensure_test_database_exists()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    
    
@pytest_asyncio.fixture
async def db():
    async with test_async_session_maker() as session:
        yield session

        await session.rollback()

        table_names = [
            _quote_identifier(table.name)
            for table in Base.metadata.sorted_tables
        ]
        if table_names:
            await session.execute(
                text(
                    "TRUNCATE TABLE "
                    f"{', '.join(table_names)} "
                    "RESTART IDENTITY CASCADE"
                )
            )
        await session.commit()
        
        
@pytest_asyncio.fixture
async def client(db):
    
    async def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:
        yield client
        
    app.dependency_overrides.clear()
    
    

@pytest.fixture
def user_data():
    return {
        "email": "test@example.com",
        "password": "12345678",
        "first_name": "Alex",
        "last_name": "Silver"
    }
   
   
@pytest.fixture
def course_data():
    return {
        "title": "Python for basics",
        "slug": "python-for-basics",
        "short_description": "A test course for testing",
        "description": "A test course to test the functionality of the service",
        "level": "Beginner",
        "price_label": "Free",
        "outcomes": ["Variables", "Loops", "Functions"],
        "is_published": False
    }
   
   
@pytest.fixture
def section_data():
    return {
        "course_id": 1,
        "title": "print & variables",
        "description": "Learn how print works",
        "order": 0,
    }
    
@pytest_asyncio.fixture
async def auth_headers(client, user_data):
    response = await client.post(
        "/api/auth/register",
        json=user_data
    )
    
    token = response.json()["token"]["access_token"]
    return {
        "Authorization": f"Bearer {token}"
    }
    

@pytest_asyncio.fixture
async def admin_headers(auth_headers, user_data, db):
    
    result = await db.execute(select(User).where(User.email == user_data["email"].lower()))
    user = result.scalars().first()
    user.role = UserRole.ADMIN
    await db.commit()
    
    return auth_headers

    
@pytest_asyncio.fixture
async def auth_expired_token_headers(client, user_data, monkeypatch):
    monkeypatch.setattr(
        settings, 
        "access_token_expire_minutes",
        -1
    )
    response = await client.post(
        "/api/auth/register",
        json=user_data
    )
    
    token = response.json()["token"]["access_token"]
    return {
        "Authorization": f"Bearer {token}"
    }
    
    
@pytest_asyncio.fixture
async def course_factory(db):
    async def create_course(
        *,
        slug,
        title="Python basics",
        is_published=False,
        short_description="A test course for testing",
        description="A test course to test the functionality of the service",
        level="Beginner",
        price_label="Free",
        outcomes=None,
    ):
        
        new_course = Course(
            slug=slug,
            title=title,
            short_description=short_description,
            description=description,
            level=level,
            price_label=price_label,
            outcomes=outcomes if outcomes is not None else ["Variables", "Loops", "Functions"],
            is_published=is_published
        )
        
        db.add(new_course)
        await db.commit()
        await db.refresh(new_course)
        return new_course

    return create_course


@pytest_asyncio.fixture
async def real_course(course_factory, course_data):
    return await course_factory(**course_data)

                
@pytest_asyncio.fixture
async def section_factory(course_factory, db):
    async def create_section(
        *,
        course_id: int | None,
        is_published: bool,
        order: int,
        title="Some section",
        description="Some description in a section"
    ):
        if course_id is None:
            course = await course_factory(slug=uuid4().hex, is_published=is_published)
            course_id = course.id
        section = Section(
            course_id=course_id,
            title=title,
            description=description,
            order=order
        )
        db.add(section)
        await db.commit()
        await db.refresh(section)
        return section

    return create_section


@pytest.fixture
def storage(tmp_path):
    return StorageService(upload_dir=tmp_path)


@pytest.fixture
def valid_png() -> UploadFile:
    with open("tests/assets/valid.png", "rb") as f:
        return UploadFile(
            filename="valid.png",
            file=BytesIO(f.read()),
            headers=Headers({"content-type": "image/png"})
        )
