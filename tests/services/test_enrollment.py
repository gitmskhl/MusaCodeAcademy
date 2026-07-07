from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException, status

from app.models import Enrollment, User
from app.services import enrollment as service_enrollment


async def create_user(
    db,
    *,
    email: str = "student@example.com",
    first_name: str = "Student",
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


async def create_enrollment(
    db,
    *,
    user_id: int,
    course_id: int,
    created_at: datetime | None = None,
) -> Enrollment:
    enrollment = Enrollment(
        user_id=user_id,
        course_id=course_id,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@pytest.mark.asyncio
async def test_enroll_creates_enrollment(course_factory, db):
    user = await create_user(db)
    course = await course_factory(slug="published", is_published=True)

    enrollment = await service_enrollment.enroll(
        course_id=course.id,
        user_id=user.id,
        db=db,
    )

    assert enrollment.id is not None
    assert enrollment.user_id == user.id
    assert enrollment.course_id == course.id
    assert enrollment.created_at is not None


@pytest.mark.asyncio
async def test_enroll_rejects_missing_course(db):
    user = await create_user(db)

    with pytest.raises(HTTPException) as exc:
        await service_enrollment.enroll(
            course_id=999_999,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_enroll_rejects_draft_course(course_factory, db):
    user = await create_user(db)
    course = await course_factory(slug="draft", is_published=False)

    with pytest.raises(HTTPException) as exc:
        await service_enrollment.enroll(
            course_id=course.id,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_enroll_rejects_duplicate_enrollment(course_factory, db):
    user = await create_user(db)
    course = await course_factory(slug="published", is_published=True)
    await service_enrollment.enroll(
        course_id=course.id,
        user_id=user.id,
        db=db,
    )

    with pytest.raises(HTTPException) as exc:
        await service_enrollment.enroll(
            course_id=course.id,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "You are already enrolled in this course."


@pytest.mark.asyncio
async def test_get_user_enrollments_returns_only_user_courses(course_factory, db):
    user = await create_user(db, email="student@example.com")
    other_user = await create_user(db, email="other@example.com")
    older_course = await course_factory(slug="older-course", is_published=True)
    newer_course = await course_factory(slug="newer-course", is_published=True)
    other_course = await course_factory(slug="other-course", is_published=True)

    now = datetime.utcnow()
    older = await create_enrollment(
        db,
        user_id=user.id,
        course_id=older_course.id,
        created_at=now - timedelta(days=1),
    )
    newer = await create_enrollment(
        db,
        user_id=user.id,
        course_id=newer_course.id,
        created_at=now,
    )
    await create_enrollment(
        db,
        user_id=other_user.id,
        course_id=other_course.id,
        created_at=now + timedelta(days=1),
    )

    enrollments = await service_enrollment.get_user_enrollments(
        user_id=user.id,
        db=db,
    )

    assert [enrollment.id for enrollment in enrollments] == [
        newer.id,
        older.id,
    ]
    assert [enrollment.course.slug for enrollment in enrollments] == [
        "newer-course",
        "older-course",
    ]


@pytest.mark.asyncio
async def test_get_user_enrollments_returns_empty_list(db):
    user = await create_user(db)

    enrollments = await service_enrollment.get_user_enrollments(
        user_id=user.id,
        db=db,
    )

    assert enrollments == []
