"""Public home uses published course data without changing protected APIs."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models import Base, Course

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def home_db():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def home_client(home_db):
    async def override_db():
        yield home_db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def course(identifier, title, published=True):
    return Course(
        id=identifier, title=title, slug=f'course-{identifier}',
        short_description=f'Описание курса {identifier}', description='Полное описание курса',
        level='Для начинающих', price_label='Бесплатно', is_published=published,
        icon_url='/uploads/images/test-cover.png',
    )


async def test_home_shows_two_published_courses_with_real_fields(home_client, home_db):
    home_db.add_all([
        course(1, 'Скрытый курс', False),
        course(5, 'Третий опубликованный'),
        course(3, 'Python <основы>'),
        course(4, 'Разработка игр'),
    ])
    await home_db.commit()
    response = await home_client.get('/')
    assert response.status_code == 200
    html = response.text
    assert html.count('class="course-card"') == 2
    assert 'Python &lt;основы&gt;' in html
    assert 'Разработка игр' in html
    assert 'Скрытый курс' not in html and 'Третий опубликованный' not in html
    assert 'href="/course-3"' in html and 'href="/course-4"' in html
    assert 'Описание курса 3' in html and 'Для начинающих' in html
    assert '/uploads/images/test-cover.png' in html


async def test_home_handles_empty_catalog_without_placeholder_courses(home_client, home_db):
    home_db.add(course(1, 'Неопубликованный курс', False))
    await home_db.commit()
    response = await home_client.get('/')
    assert response.status_code == 200
    assert 'Курсы скоро появятся.' in response.text
    assert 'class="course-card"' not in response.text


async def test_student_pages_share_design_and_course_api_remains_protected(home_client):
    for path in (
        '/courses', '/login', '/register', '/dashboard', '/course-3',
        '/course-3/sections', '/course-3/sections/1/lessons', '/course-3/steps/1',
        '/notifications', '/homework', '/forgot-password', '/reset-password?token=test',
    ):
        response = await home_client.get(path)
        assert response.status_code == 200
        assert 'css/home.css' not in response.text
        assert 'data-design-system="mca-v1"' in response.text
        assert 'images/home-mark.svg' in response.text
    for path in ('/admin', '/admin/notifications', '/admin/steps/1', '/admin/steps/1/task'):
        response = await home_client.get(path)
        assert response.status_code == 200
        assert 'css/student.css' not in response.text
        assert 'data-design-system="mca-v1"' not in response.text
    assert (await home_client.get('/api/courses')).status_code == 401
