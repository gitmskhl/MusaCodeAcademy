from pathlib import Path

import pytest
from fastapi import status

from app.models import Lesson, Section
from app.api.routers import file as file_router
from app.services.storage import StorageService


PUBLIC_COURSE_FIELDS = {
    "id",
    "title",
    "slug",
    "short_description",
    "description",
    "level",
    "price_label",
    "outcomes",
    "promo_video_url",
    "icon_url",
}
ADMIN_COURSE_FIELDS = PUBLIC_COURSE_FIELDS | {
    "is_published",
    "created_at",
    "updated_at",
}
PUBLIC_SECTION_FIELDS = {
    "id",
    "course_id",
    "title",
    "description",
    "order",
}
ADMIN_SECTION_FIELDS = PUBLIC_SECTION_FIELDS | {
    "created_at",
    "updated_at",
}
COURSE_INFO_FIELDS = PUBLIC_COURSE_FIELDS | {
    "is_enrolled",
    "lessons_count",
    "sections_count",
    "sections",
}
SECTION_SHORT_INFO_FIELDS = {
    "id",
    "title",
    "description",
    "order",
    "lessons",
}
LESSON_SHORT_INFO_FIELDS = {
    "id",
    "title",
    "order",
}


async def enroll_in_course(client, auth_headers, course_id: int):
    response = await client.post(
        f"/api/courses/{course_id}/enroll",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED


def assert_public_course(data, course):
    assert set(data) == PUBLIC_COURSE_FIELDS
    assert data["id"] == course.id
    assert data["title"] == course.title
    assert data["slug"] == course.slug
    assert data["short_description"] == course.short_description
    assert data["description"] == course.description
    assert data["level"] == course.level
    assert data["price_label"] == course.price_label
    assert data["outcomes"] == course.outcomes
    assert data["icon_url"] == course.icon_url


async def create_section(
    db,
    *,
    course_id,
    title="Introduction",
    description="A detailed section description",
    order=0,
):
    section = Section(
        course_id=course_id,
        title=title,
        description=description,
        order=order,
    )
    db.add(section)
    await db.commit()
    await db.refresh(section)
    return section


async def create_lesson(
    db,
    *,
    section_id,
    title="Test lesson",
    description="Detailed lesson description",
    order=0,
):
    lesson = Lesson(
        section_id=section_id,
        title=title,
        description=description,
        order=order,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


# POST /api/courses


@pytest.mark.asyncio
async def test_create_course_success(client, admin_headers, course_data):
    course_data["slug"] = "Python-For-Basics"

    response = await client.post(
        "/api/courses",
        json=course_data,
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == PUBLIC_COURSE_FIELDS
    assert data["id"] is not None
    assert data["title"] == course_data["title"]
    assert data["slug"] == course_data["slug"].lower()
    assert data["short_description"] == course_data["short_description"]
    assert data["description"] == course_data["description"]
    assert data["level"] == course_data["level"]
    assert data["price_label"] == course_data["price_label"]
    assert data["outcomes"] == course_data["outcomes"]


@pytest.mark.asyncio
async def test_create_course_is_draft_by_default(
    client,
    admin_headers,
    course_data,
):
    course_data["is_published"] = True

    create_response = await client.post(
        "/api/courses",
        json=course_data,
        headers=admin_headers,
    )
    course_id = create_response.json()["id"]
    admin_response = await client.get(
        f"/api/courses/{course_id}/admin",
        headers=admin_headers,
    )

    assert create_response.status_code == status.HTTP_201_CREATED
    assert admin_response.status_code == status.HTTP_200_OK
    assert admin_response.json()["is_published"] is False


@pytest.mark.asyncio
async def test_create_course_not_admin(client, auth_headers, course_data):
    response = await client.post(
        "/api/courses",
        json=course_data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_create_course_without_token(client, course_data):
    response = await client.post("/api/courses", json=course_data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_create_course_taken_slug_case_insensitive(
    client,
    admin_headers,
    course_factory,
    course_data,
):
    await course_factory(slug="python-taken")
    course_data["slug"] = "PYTHON-TAKEN"

    response = await client.post(
        "/api/courses",
        json=course_data,
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "detail": "Course with this slug already exists"
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "abcd"),
        ("slug", "x"),
        ("short_description", "too short"),
        ("description", "too short"),
        ("level", "x"),
        ("price_label", "x"),
        ("outcomes", ["x" * 121]),
    ],
)
async def test_create_course_validates_payload(
    client,
    admin_headers,
    course_data,
    field,
    value,
):
    course_data[field] = value

    response = await client.post(
        "/api/courses",
        json=course_data,
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["body", field]


@pytest.mark.asyncio
async def test_create_course_requires_all_fields(client, admin_headers):
    response = await client.post(
        "/api/courses",
        json={},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert {error["loc"][-1] for error in response.json()["detail"]} == {
        "title",
        "slug",
        "short_description",
        "description",
    }


# GET /api/courses


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/courses",
        "/api/courses/slug/python",
        "/api/courses/1",
        "/api/courses/1/sections",
        "/api/sections/1",
        "/api/sections/1/lessons",
        "/api/lessons/1",
        "/api/lessons/1/steps",
        "/api/steps/1",
        "/api/steps/1/viewer?course_slug=python",
    ],
)
async def test_course_content_requires_authentication(client, path):
    response = await client.get(path)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_courses_returns_empty_list(client, auth_headers):
    response = await client.get("/api/courses", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_courses_returns_only_published_courses(
    client,
    course_factory,
    auth_headers,
):
    published = await course_factory(
        slug="published",
        title="Published course",
        is_published=True,
    )
    await course_factory(
        slug="draft",
        title="Draft course",
        is_published=False,
    )

    response = await client.get("/api/courses", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert_public_course(response.json()[0], published)


# GET /api/courses/slug/{course_slug}


@pytest.mark.asyncio
async def test_get_course_page_returns_course_sections_and_lessons(
    client,
    course_factory,
    db,
    auth_headers,
):
    course = await course_factory(
        slug="python-basics",
        title="Python basics",
        is_published=True,
    )
    second_section = await create_section(
        db,
        course_id=course.id,
        title="Second section",
        order=1,
    )
    first_section = await create_section(
        db,
        course_id=course.id,
        title="First section",
        order=0,
    )
    second_lesson = await create_lesson(
        db,
        section_id=first_section.id,
        title="Second lesson",
        order=1,
    )
    first_lesson = await create_lesson(
        db,
        section_id=first_section.id,
        title="First lesson",
        order=0,
    )
    await create_lesson(
        db,
        section_id=second_section.id,
        title="Another lesson",
        order=0,
    )

    response = await client.get(
        "/api/courses/slug/PYTHON-BASICS",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert set(data) == COURSE_INFO_FIELDS
    assert data["id"] == course.id
    assert data["title"] == "Python basics"
    assert data["slug"] == "python-basics"
    assert data["level"] == course.level
    assert data["price_label"] == course.price_label
    assert data["outcomes"] == course.outcomes
    assert data["is_enrolled"] is False
    assert data["lessons_count"] == 3
    assert data["sections_count"] == 2
    assert [section["id"] for section in data["sections"]] == [
        first_section.id,
        second_section.id,
    ]
    assert all(set(section) == SECTION_SHORT_INFO_FIELDS for section in data["sections"])
    assert [lesson["id"] for lesson in data["sections"][0]["lessons"]] == [
        first_lesson.id,
        second_lesson.id,
    ]
    assert all(
        set(lesson) == LESSON_SHORT_INFO_FIELDS
        for section in data["sections"]
        for lesson in section["lessons"]
    )


@pytest.mark.asyncio
async def test_get_course_page_returns_empty_sections(
    client,
    course_factory,
    auth_headers,
):
    course = await course_factory(slug="empty-course", is_published=True)

    response = await client.get(
        f"/api/courses/slug/{course.slug}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == course.id
    assert data["is_enrolled"] is False
    assert data["lessons_count"] == 0
    assert data["sections_count"] == 0
    assert data["sections"] == []


@pytest.mark.asyncio
async def test_get_course_page_returns_is_enrolled_true_after_enrollment(
    client,
    course_factory,
    auth_headers,
):
    course = await course_factory(slug="enrolled-course", is_published=True)
    enroll_response = await client.post(
        f"/api/courses/{course.id}/enroll",
        headers=auth_headers,
    )

    response = await client.get(
        f"/api/courses/slug/{course.slug}",
        headers=auth_headers,
    )

    assert enroll_response.status_code == status.HTTP_201_CREATED
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_enrolled"] is True


@pytest.mark.asyncio
async def test_get_course_page_hides_draft(
    client,
    course_factory,
    auth_headers,
):
    await course_factory(slug="draft-course", is_published=False)

    response = await client.get(
        "/api/courses/slug/draft-course",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_course_page_not_found(client, auth_headers):
    response = await client.get(
        "/api/courses/slug/missing-course",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


# GET /api/courses/{course_id}


@pytest.mark.asyncio
async def test_get_published_course_success(client, course_factory, auth_headers):
    course = await course_factory(slug="published", is_published=True)

    response = await client.get(
        f"/api/courses/{course.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert_public_course(response.json(), course)


@pytest.mark.asyncio
async def test_get_course_rejects_draft(client, course_factory, auth_headers):
    course = await course_factory(slug="draft", is_published=False)

    response = await client.get(
        f"/api/courses/{course.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Course is not published"}


@pytest.mark.asyncio
async def test_get_course_not_found(client, auth_headers):
    response = await client.get(
        "/api/courses/999999",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_course_rejects_invalid_id(client, auth_headers):
    response = await client.get(
        "/api/courses/not-an-id",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "course_id"]


# GET /api/courses/admin


@pytest.mark.asyncio
async def test_get_courses_admin_returns_published_and_drafts(
    client,
    admin_headers,
    course_factory,
):
    published = await course_factory(slug="published", is_published=True)
    draft = await course_factory(slug="draft", is_published=False)

    response = await client.get(
        "/api/courses/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    courses = {course["id"]: course for course in response.json()}
    assert set(courses) == {published.id, draft.id}
    assert all(set(course) == ADMIN_COURSE_FIELDS for course in courses.values())
    assert courses[published.id]["is_published"] is True
    assert courses[draft.id]["is_published"] is False
    assert all(course["created_at"] for course in courses.values())
    assert all(course["updated_at"] for course in courses.values())


@pytest.mark.asyncio
async def test_get_courses_admin_returns_empty_list(client, admin_headers):
    response = await client.get(
        "/api/courses/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_courses_admin_rejects_non_admin(client, auth_headers):
    response = await client.get(
        "/api/courses/admin",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_courses_admin_requires_authentication(client):
    response = await client.get("/api/courses/admin")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# GET /api/courses/{course_id}/admin


@pytest.mark.asyncio
async def test_get_course_admin_returns_draft(
    client,
    admin_headers,
    course_factory,
):
    course = await course_factory(slug="draft", is_published=False)

    response = await client.get(
        f"/api/courses/{course.id}/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert set(data) == ADMIN_COURSE_FIELDS
    assert data["id"] == course.id
    assert data["slug"] == course.slug
    assert data["is_published"] is False
    assert data["created_at"]
    assert data["updated_at"]


@pytest.mark.asyncio
async def test_get_course_admin_not_found(client, admin_headers):
    response = await client.get(
        "/api/courses/999999/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_course_admin_rejects_non_admin(
    client,
    auth_headers,
    course_factory,
):
    course = await course_factory(slug="draft")

    response = await client.get(
        f"/api/courses/{course.id}/admin",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_course_admin_requires_authentication(client, course_factory):
    course = await course_factory(slug="draft")

    response = await client.get(f"/api/courses/{course.id}/admin")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# PATCH /api/courses/{course_id}


@pytest.mark.asyncio
async def test_update_course_success(
    client,
    admin_headers,
    course_factory,
):
    course = await course_factory(
        slug="python",
        title="Python basics",
        is_published=False,
    )
    original_description = course.description

    response = await client.patch(
        f"/api/courses/{course.id}",
        json={
            "title": "Advanced Python",
            "slug": "FASTAPI",
            "level": "Advanced",
            "price_label": "$49",
            "outcomes": ["Async Python", "FastAPI APIs"],
            "is_published": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert set(data) == PUBLIC_COURSE_FIELDS
    assert data["title"] == "Advanced Python"
    assert data["slug"] == "fastapi"
    assert data["description"] == original_description
    assert data["level"] == "Advanced"
    assert data["price_label"] == "$49"
    assert data["outcomes"] == ["Async Python", "FastAPI APIs"]

    admin_response = await client.get(
        f"/api/courses/{course.id}/admin",
        headers=admin_headers,
    )
    assert admin_response.json()["is_published"] is True


@pytest.mark.asyncio
async def test_update_course_accepts_empty_payload(
    client,
    admin_headers,
    course_factory,
):
    course = await course_factory(slug="python", title="Python basics")

    response = await client.patch(
        f"/api/courses/{course.id}",
        json={},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert_public_course(response.json(), course)


@pytest.mark.asyncio
async def test_update_course_allows_same_slug_with_different_case(
    client,
    admin_headers,
    course_factory,
):
    course = await course_factory(slug="python")

    response = await client.patch(
        f"/api/courses/{course.id}",
        json={"slug": "PYTHON"},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["slug"] == "python"


@pytest.mark.asyncio
async def test_update_course_duplicate_slug_returns_conflict(
    client,
    admin_headers,
    course_factory,
):
    course = await course_factory(slug="python")
    await course_factory(slug="fastapi")

    response = await client.patch(
        f"/api/courses/{course.id}",
        json={"slug": "FASTAPI"},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "detail": "Course with this slug already exists"
    }


@pytest.mark.asyncio
async def test_update_course_not_found(client, admin_headers):
    response = await client.patch(
        "/api/courses/999999",
        json={"title": "Advanced Python"},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_update_course_rejects_non_admin(
    client,
    auth_headers,
    course_factory,
):
    course = await course_factory(slug="python")

    response = await client.patch(
        f"/api/courses/{course.id}",
        json={"title": "Advanced Python"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_course_requires_authentication(client, course_factory):
    course = await course_factory(slug="python")

    response = await client.patch(
        f"/api/courses/{course.id}",
        json={"title": "Advanced Python"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "abcd"),
        ("slug", "x"),
        ("short_description", "too short"),
        ("description", "too short"),
        ("level", "x"),
        ("price_label", "x"),
        ("outcomes", ["x" * 121]),
    ],
)
async def test_update_course_validates_payload(
    client,
    admin_headers,
    course_factory,
    field,
    value,
):
    course = await course_factory(slug="python")

    response = await client.patch(
        f"/api/courses/{course.id}",
        json={field: value},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["body", field]


# DELETE /api/courses/{course_id}


@pytest.mark.asyncio
async def test_delete_course_success(
    client,
    admin_headers,
    course_factory,
):
    course = await course_factory(slug="course-to-delete")

    response = await client.delete(
        f"/api/courses/{course.id}",
        headers=admin_headers,
    )
    get_response = await client.get(
        f"/api/courses/{course.id}/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_course_not_found(client, admin_headers):
    response = await client.delete(
        "/api/courses/999999",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_delete_course_rejects_non_admin(
    client,
    auth_headers,
    course_factory,
):
    course = await course_factory(slug="course-to-delete")

    response = await client.delete(
        f"/api/courses/{course.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_course_requires_authentication(client, course_factory):
    course = await course_factory(slug="course-to-delete")

    response = await client.delete(f"/api/courses/{course.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# GET /api/courses/{course_id}/sections


@pytest.mark.asyncio
async def test_get_course_sections_returns_sections_in_order(
    client,
    course_factory,
    db,
    auth_headers,
):
    course = await course_factory(slug="published", is_published=True)
    second = await create_section(
        db,
        course_id=course.id,
        title="Second section",
        order=1,
    )
    first = await create_section(
        db,
        course_id=course.id,
        title="First section",
        order=0,
    )
    await enroll_in_course(client, auth_headers, course.id)

    response = await client.get(
        f"/api/courses/{course.id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [section["id"] for section in data] == [first.id, second.id]
    assert all(set(section) == PUBLIC_SECTION_FIELDS for section in data)
    assert [section["order"] for section in data] == [0, 1]


@pytest.mark.asyncio
async def test_get_course_sections_returns_empty_list(
    client,
    course_factory,
    auth_headers,
):
    course = await course_factory(slug="published", is_published=True)
    await enroll_in_course(client, auth_headers, course.id)

    response = await client.get(
        f"/api/courses/{course.id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_course_sections_requires_enrollment(
    client,
    course_factory,
    auth_headers,
):
    course = await course_factory(slug="published", is_published=True)

    response = await client.get(
        f"/api/courses/{course.id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Enrollment required"}


@pytest.mark.asyncio
async def test_get_course_sections_hides_draft(
    client,
    course_factory,
    auth_headers,
):
    course = await course_factory(slug="draft", is_published=False)

    response = await client.get(
        f"/api/courses/{course.id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_course_sections_course_not_found(client, auth_headers):
    response = await client.get(
        "/api/courses/999999/sections",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


# POST /api/courses/{course_id}/sections


@pytest.mark.asyncio
async def test_create_course_section_success(
    client,
    admin_headers,
    course_factory,
):
    course = await course_factory(slug="course")

    response = await client.post(
        f"/api/courses/{course.id}/sections",
        json={
            "title": "Introduction",
            "description": "A detailed section description",
        },
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == PUBLIC_SECTION_FIELDS
    assert data["id"] is not None
    assert data["course_id"] == course.id
    assert data["title"] == "Introduction"
    assert data["description"] == "A detailed section description"
    assert data["order"] == 0


@pytest.mark.asyncio
async def test_create_course_section_appends_after_existing_section(
    client,
    admin_headers,
    course_factory,
    db,
):
    course = await course_factory(slug="course")
    await create_section(db, course_id=course.id, order=3)

    response = await client.post(
        f"/api/courses/{course.id}/sections",
        json={"title": "Next section"},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["description"] is None
    assert response.json()["order"] == 4


@pytest.mark.asyncio
async def test_create_course_section_course_not_found(client, admin_headers):
    response = await client.post(
        "/api/courses/999999/sections",
        json={"title": "Introduction"},
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_create_course_section_rejects_non_admin(
    client,
    auth_headers,
    course_factory,
):
    course = await course_factory(slug="course")

    response = await client.post(
        f"/api/courses/{course.id}/sections",
        json={"title": "Introduction"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_course_section_requires_authentication(
    client,
    course_factory,
):
    course = await course_factory(slug="course")

    response = await client.post(
        f"/api/courses/{course.id}/sections",
        json={"title": "Introduction"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"title": "ab"},
        {"title": "Introduction", "description": "short"},
    ],
)
async def test_create_course_section_validates_payload(
    client,
    admin_headers,
    course_factory,
    payload,
):
    course = await course_factory(slug="course")

    response = await client.post(
        f"/api/courses/{course.id}/sections",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# GET /api/courses/{course_id}/sections/admin


@pytest.mark.asyncio
async def test_get_course_sections_admin_returns_draft_sections(
    client,
    admin_headers,
    course_factory,
    db,
):
    course = await course_factory(slug="draft", is_published=False)
    section = await create_section(db, course_id=course.id)

    response = await client.get(
        f"/api/courses/{course.id}/sections/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    data = response.json()[0]
    assert set(data) == ADMIN_SECTION_FIELDS
    assert data["id"] == section.id
    assert data["course_id"] == course.id
    assert data["created_at"]
    assert data["updated_at"]


@pytest.mark.asyncio
async def test_get_course_sections_admin_course_not_found(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/courses/999999/sections/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_course_sections_admin_rejects_non_admin(
    client,
    auth_headers,
    course_factory,
):
    course = await course_factory(slug="draft")

    response = await client.get(
        f"/api/courses/{course.id}/sections/admin",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_course_sections_admin_requires_authentication(
    client,
    course_factory,
):
    course = await course_factory(slug="draft")

    response = await client.get(
        f"/api/courses/{course.id}/sections/admin",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_course_promo_video_lifecycle(client, admin_headers, course_data):
    url = "https://kinescope.io/embed/mmmLhAmqMPRxgfuLqW9Z91"
    response = await client.post(
        "/api/courses", headers=admin_headers,
        json={**course_data, "promo_video_url": f'<iframe src="{url}" onload="alert(1)"></iframe>'},
    )
    assert response.status_code == 201
    course_id = response.json()["id"]
    assert response.json()["promo_video_url"] == url
    response = await client.patch(
        f"/api/courses/{course_id}", headers=admin_headers,
        json={"is_published": True},
    )
    assert response.status_code == 200
    assert response.json()["promo_video_url"] == url
    response = await client.get(f"/api/courses/slug/{course_data['slug']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["promo_video_url"] == url
    for invalid in ['https://example.com/embed/123', 'javascript:alert(1)', '<iframe></iframe>']:
        response = await client.patch(
            f"/api/courses/{course_id}", headers=admin_headers,
            json={"promo_video_url": invalid},
        )
        assert response.status_code == 422
    for empty in ["", None]:
        response = await client.patch(
            f"/api/courses/{course_id}", headers=admin_headers,
            json={"promo_video_url": empty},
        )
        assert response.status_code == 200
        assert response.json()["promo_video_url"] is None


@pytest.mark.asyncio
async def test_course_icon_upload_lifecycle(
    client, admin_headers, user_data, course_data, monkeypatch, tmp_path,
):
    storage = StorageService(tmp_path)
    monkeypatch.setattr(file_router, "storage_service", storage)
    upload = await client.post(
        "/api/files/images", headers=admin_headers,
        files={"file": ("icon.png", Path("tests/assets/valid.png").read_bytes(), "image/png")},
    )
    assert upload.status_code == 201
    storage_path = upload.json()["storage_path"]
    assert (tmp_path / storage_path).is_file()
    icon_url = storage.make_url(storage_path)

    created = await client.post(
        "/api/courses", headers=admin_headers, json={**course_data, "icon_url": icon_url},
    )
    assert created.status_code == 201
    assert created.json()["icon_url"] == icon_url
    course_id = created.json()["id"]
    endpoint = f"/api/courses/{course_id}"

    # Saving unrelated course fields must preserve the icon.
    published = await client.patch(endpoint, headers=admin_headers, json={"is_published": True})
    assert published.status_code == 200
    assert published.json()["icon_url"] == icon_url
    for url in [f"{endpoint}/admin", f"/api/courses/slug/{course_data['slug']}"]:
        loaded = await client.get(url, headers=admin_headers)
        assert loaded.status_code == 200
        assert loaded.json()["icon_url"] == icon_url
    student = await client.post(
        "/api/auth/register", json={**user_data, "email": "icon-student@example.com"},
    )
    assert student.status_code == 201
    student_headers = {"Authorization": f"Bearer {student.json()['token']['access_token']}"}
    catalog = await client.get("/api/courses", headers=student_headers)
    assert catalog.status_code == 200
    assert next(course for course in catalog.json() if course["id"] == course_id)["icon_url"] == icon_url

    rejected = await client.patch(endpoint, headers=student_headers, json={"icon_url": None})
    assert rejected.status_code == 403
    replacement = await client.post(
        "/api/files/images", headers=admin_headers,
        files={"file": ("replacement.png", Path("tests/assets/valid.png").read_bytes(), "image/png")},
    )
    assert replacement.status_code == 201
    next_url = storage.make_url(replacement.json()["storage_path"])
    updated = await client.patch(endpoint, headers=admin_headers, json={"icon_url": next_url})
    assert updated.status_code == 200
    assert updated.json()["icon_url"] == next_url
    cleared = await client.patch(endpoint, headers=admin_headers, json={"icon_url": None})
    assert cleared.status_code == 200
    assert cleared.json()["icon_url"] is None
    reloaded = await client.get(f"{endpoint}/admin", headers=admin_headers)
    assert reloaded.json()["icon_url"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("icon_url", [
    "https://example.com/icon.png", "javascript:alert(1)",
    "/uploads/images/../icon.png", "/uploads/images/icon.svg",
])
async def test_course_icon_rejects_invalid_paths(client, admin_headers, course_data, icon_url):
    rejected = await client.post(
        "/api/courses", headers=admin_headers, json={**course_data, "icon_url": icon_url},
    )
    assert rejected.status_code == 422
    created = await client.post("/api/courses", headers=admin_headers, json=course_data)
    assert created.status_code == 201
    assert created.json()["icon_url"] is None
    rejected = await client.patch(
        f"/api/courses/{created.json()['id']}", headers=admin_headers, json={"icon_url": icon_url},
    )
    assert rejected.status_code == 422
