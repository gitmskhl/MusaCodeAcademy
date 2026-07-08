import pytest
from fastapi import status
from sqlalchemy import select

from app.models import Enrollment, User


ENROLLMENT_FIELDS = {
    "id",
    "user_id",
    "course_id",
    "created_at",
}
COURSE_FIELDS = {
    "id",
    "title",
    "slug",
    "short_description",
    "description",
    "level",
    "price_label",
    "outcomes",
}
ENROLLMENT_WITH_COURSE_FIELDS = ENROLLMENT_FIELDS | {"course"}


async def get_user_by_email(db, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalars().one()


async def create_user(
    db,
    *,
    email: str = "other@example.com",
    first_name: str = "Other",
    last_name: str = "User",
) -> User:
    user = User(
        email=email,
        password_hash="hashed-password",
        first_name=first_name,
        last_name=last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_enrollment(db, *, user_id: int, course_id: int) -> Enrollment:
    enrollment = Enrollment(user_id=user_id, course_id=course_id)
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@pytest.mark.asyncio
async def test_enroll_course_success(client, auth_headers, course_factory, db, user_data):
    course = await course_factory(slug="published", is_published=True)
    user = await get_user_by_email(db, user_data["email"])

    response = await client.post(
        f"/api/courses/{course.id}/enroll",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == ENROLLMENT_FIELDS
    assert data["id"] is not None
    assert data["user_id"] == user.id
    assert data["course_id"] == course.id
    assert data["created_at"]


@pytest.mark.asyncio
async def test_enroll_course_requires_authentication(client, course_factory):
    course = await course_factory(slug="published", is_published=True)

    response = await client.post(f"/api/courses/{course.id}/enroll")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_enroll_course_not_found(client, auth_headers):
    response = await client.post(
        "/api/courses/999999/enroll",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_enroll_course_rejects_draft(client, auth_headers, course_factory):
    course = await course_factory(slug="draft", is_published=False)

    response = await client.post(
        f"/api/courses/{course.id}/enroll",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_enroll_course_rejects_duplicate(client, auth_headers, course_factory):
    course = await course_factory(slug="published", is_published=True)
    await client.post(
        f"/api/courses/{course.id}/enroll",
        headers=auth_headers,
    )

    response = await client.post(
        f"/api/courses/{course.id}/enroll",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "detail": "You are already enrolled in this course."
    }


@pytest.mark.asyncio
async def test_get_my_enrollments_returns_current_user_courses(
    client,
    auth_headers,
    course_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    other_user = await create_user(db)
    first_course = await course_factory(
        slug="first-course",
        title="First course",
        is_published=True,
    )
    second_course = await course_factory(
        slug="second-course",
        title="Second course",
        is_published=True,
    )
    other_course = await course_factory(
        slug="other-course",
        title="Other course",
        is_published=True,
    )
    first_enrollment = await create_enrollment(
        db,
        user_id=user.id,
        course_id=first_course.id,
    )
    second_enrollment = await create_enrollment(
        db,
        user_id=user.id,
        course_id=second_course.id,
    )
    await create_enrollment(
        db,
        user_id=other_user.id,
        course_id=other_course.id,
    )

    response = await client.get("/api/enrollments/me", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert {enrollment["id"] for enrollment in data} == {
        first_enrollment.id,
        second_enrollment.id,
    }
    assert all(set(enrollment) == ENROLLMENT_WITH_COURSE_FIELDS for enrollment in data)
    assert all(set(enrollment["course"]) == COURSE_FIELDS for enrollment in data)
    assert {enrollment["course"]["slug"] for enrollment in data} == {
        "first-course",
        "second-course",
    }


@pytest.mark.asyncio
async def test_get_my_enrollments_returns_empty_list(client, auth_headers):
    response = await client.get("/api/enrollments/me", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_my_enrollments_requires_authentication(client):
    response = await client.get("/api/enrollments/me")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
