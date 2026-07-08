import select
from io import BytesIO
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
import pytest
import pytest_asyncio
from fastapi import UploadFile
from starlette.datastructures import Headers
from sqlalchemy import delete, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import get_db
from app.enums import UserRole
from app.models import Base, Course, User, Section
from app.main import app
from app.core.config import settings
from app.services.storage import StorageService


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

test_async_session_maker = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False,
    class_=AsyncSession
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
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
        
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(delete(table))
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
