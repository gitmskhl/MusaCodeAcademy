import select

from httpx import AsyncClient, ASGITransport
import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import get_db
from app.enums import UserRole
from app.models import Base, Course, User
from app.main import app
from app.core.config import settings


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
    async def create_course(*, slug, title="Python basics", is_published=False):
        
        new_course = Course(
            slug=slug,
            title=title,
            short_description="A test course for testing",
            description="A test course to test the functionality of the service",
            is_published=is_published
        )
        
        db.add(new_course)
        await db.commit()
        await db.refresh(new_course)
        return new_course

    return create_course

