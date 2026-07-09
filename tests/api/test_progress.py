import pytest
from fastapi import status
from sqlalchemy import select

from app.models import Enrollment, Lesson, Step, StepProgress, User


PROGRESS_FIELDS = {
    "id",
    "user_id",
    "step_id",
    "completed_at",
}


async def get_user_by_email(db, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalars().one()


async def create_user(db, *, email: str = "other@example.com") -> User:
    user = User(
        email=email,
        password_hash="hashed-password",
        first_name="Other",
        last_name="User",
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


async def create_lesson(db, *, section_id: int) -> Lesson:
    lesson = Lesson(
        section_id=section_id,
        title="Variables",
        description="Learn variables",
        order=0,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def create_step(
    db,
    *,
    lesson_id: int,
    title: str = "First step",
    order: int = 0,
) -> Step:
    step = Step(
        lesson_id=lesson_id,
        title=title,
        order=order,
        content={"layout": "single", "blocks": []},
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def create_step_target(
    db,
    section_factory,
    *,
    is_published: bool = True,
):
    section = await section_factory(
        course_id=None,
        is_published=is_published,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_step(db, lesson_id=lesson.id)
    return section.course_id, lesson, step


@pytest.mark.asyncio
async def test_complete_step_success(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, _, step = await create_step_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)

    response = await client.post(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == PROGRESS_FIELDS
    assert data["user_id"] == user.id
    assert data["step_id"] == step.id
    assert data["completed_at"]


@pytest.mark.asyncio
async def test_complete_step_requires_authentication(client, section_factory, db):
    _, _, step = await create_step_target(db, section_factory)

    response = await client.post(f"/api/progress/steps/{step.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_complete_step_rejects_user_without_enrollment(
    client,
    auth_headers,
    section_factory,
    db,
):
    _, _, step = await create_step_target(db, section_factory)

    response = await client.post(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Enrollment not found"}


@pytest.mark.asyncio
async def test_complete_step_rejects_draft_course(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, _, step = await create_step_target(
        db,
        section_factory,
        is_published=False,
    )
    await create_enrollment(db, user_id=user.id, course_id=course_id)

    response = await client.post(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_step_progress_returns_completed_status(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, _, step = await create_step_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    await client.post(f"/api/progress/steps/{step.id}", headers=auth_headers)

    response = await client.get(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"completed": True}


@pytest.mark.asyncio
async def test_get_step_progress_is_scoped_to_current_user(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    current_user = await get_user_by_email(db, user_data["email"])
    other_user = await create_user(db)
    course_id, _, step = await create_step_target(db, section_factory)
    await create_enrollment(db, user_id=current_user.id, course_id=course_id)
    await create_enrollment(db, user_id=other_user.id, course_id=course_id)
    db.add(StepProgress(user_id=other_user.id, step_id=step.id))
    await db.commit()

    response = await client.get(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"completed": False}


@pytest.mark.asyncio
async def test_uncomplete_step_deletes_progress(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, _, step = await create_step_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    response = await client.post(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )
    progress_id = response.json()["id"]

    response = await client.delete(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert await db.get(StepProgress, progress_id) is None


@pytest.mark.asyncio
async def test_uncomplete_step_requires_authentication(client, section_factory, db):
    _, _, step = await create_step_target(db, section_factory)

    response = await client.delete(f"/api/progress/steps/{step.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_lesson_progress_success(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, lesson, first_step = await create_step_target(db, section_factory)
    second_step = await create_step(
        db,
        lesson_id=lesson.id,
        title="Second step",
        order=1,
    )
    third_step = await create_step(
        db,
        lesson_id=lesson.id,
        title="Third step",
        order=2,
    )
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    await client.post(
        f"/api/progress/steps/{third_step.id}",
        headers=auth_headers,
    )
    await client.post(
        f"/api/progress/steps/{first_step.id}",
        headers=auth_headers,
    )

    response = await client.get(
        f"/api/progress/lessons/{lesson.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "lesson_id": lesson.id,
        "completed_step_ids": [first_step.id, third_step.id],
        "completed_count": 2,
        "total_count": 3,
        "percent": 67,
    }
    assert second_step.id not in response.json()["completed_step_ids"]


@pytest.mark.asyncio
async def test_get_lesson_progress_requires_authentication(
    client,
    section_factory,
    db,
):
    _, lesson, _ = await create_step_target(db, section_factory)

    response = await client.get(f"/api/progress/lessons/{lesson.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_lesson_progress_rejects_user_without_enrollment(
    client,
    auth_headers,
    section_factory,
    db,
):
    _, lesson, _ = await create_step_target(db, section_factory)

    response = await client.get(
        f"/api/progress/lessons/{lesson.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Enrollment not found"}


@pytest.mark.asyncio
async def test_get_lesson_progress_rejects_draft_course(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, lesson, _ = await create_step_target(
        db,
        section_factory,
        is_published=False,
    )
    await create_enrollment(db, user_id=user.id, course_id=course_id)

    response = await client.get(
        f"/api/progress/lessons/{lesson.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_lesson_progress_ignores_other_users_progress(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    current_user = await get_user_by_email(db, user_data["email"])
    other_user = await create_user(db)
    course_id, lesson, step = await create_step_target(db, section_factory)
    await create_enrollment(db, user_id=current_user.id, course_id=course_id)
    await create_enrollment(db, user_id=other_user.id, course_id=course_id)
    db.add(StepProgress(user_id=other_user.id, step_id=step.id))
    await db.commit()

    response = await client.get(
        f"/api/progress/lessons/{lesson.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "lesson_id": lesson.id,
        "completed_step_ids": [],
        "completed_count": 0,
        "total_count": 1,
        "percent": 0,
    }


@pytest.mark.asyncio
async def test_get_course_sections_progress_success(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    first_section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    second_section = await section_factory(
        course_id=first_section.course_id,
        is_published=True,
        order=1,
    )
    first_lesson = await create_lesson(db, section_id=first_section.id)
    second_lesson = await create_lesson(db, section_id=first_section.id)
    first_step = await create_step(
        db,
        lesson_id=first_lesson.id,
        title="First lesson step 1",
        order=0,
    )
    second_step = await create_step(
        db,
        lesson_id=first_lesson.id,
        title="First lesson step 2",
        order=1,
    )
    third_step = await create_step(
        db,
        lesson_id=second_lesson.id,
        title="Second lesson step 1",
        order=0,
    )
    await create_step(
        db,
        lesson_id=second_lesson.id,
        title="Second lesson step 2",
        order=1,
    )
    await create_enrollment(
        db,
        user_id=user.id,
        course_id=first_section.course_id,
    )
    for step in [first_step, second_step, third_step]:
        await client.post(
            f"/api/progress/steps/{step.id}",
            headers=auth_headers,
        )

    response = await client.get(
        f"/api/progress/courses/{first_section.course_id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "course_id": first_section.course_id,
        "sections": [
            {
                "section_id": first_section.id,
                "completed_step_count": 3,
                "total_step_count": 4,
                "completed_lesson_count": 1,
                "total_lesson_count": 2,
                "percent": 75,
            },
            {
                "section_id": second_section.id,
                "completed_step_count": 0,
                "total_step_count": 0,
                "completed_lesson_count": 0,
                "total_lesson_count": 0,
                "percent": 0,
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_course_sections_progress_requires_authentication(
    client,
    course_factory,
):
    course = await course_factory(slug="published", is_published=True)

    response = await client.get(f"/api/progress/courses/{course.id}/sections")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_course_sections_progress_rejects_user_without_enrollment(
    client,
    auth_headers,
    course_factory,
):
    course = await course_factory(slug="published", is_published=True)

    response = await client.get(
        f"/api/progress/courses/{course.id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Enrollment not found"}


@pytest.mark.asyncio
async def test_get_course_sections_progress_rejects_draft_course(
    client,
    auth_headers,
    course_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course = await course_factory(slug="draft", is_published=False)
    await create_enrollment(db, user_id=user.id, course_id=course.id)

    response = await client.get(
        f"/api/progress/courses/{course.id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_course_sections_progress_ignores_other_users_progress(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    current_user = await get_user_by_email(db, user_data["email"])
    other_user = await create_user(db)
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_step(db, lesson_id=lesson.id)
    await create_enrollment(
        db,
        user_id=current_user.id,
        course_id=section.course_id,
    )
    await create_enrollment(
        db,
        user_id=other_user.id,
        course_id=section.course_id,
    )
    db.add(StepProgress(user_id=other_user.id, step_id=step.id))
    await db.commit()

    response = await client.get(
        f"/api/progress/courses/{section.course_id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "course_id": section.course_id,
        "sections": [
            {
                "section_id": section.id,
                "completed_step_count": 0,
                "total_step_count": 1,
                "completed_lesson_count": 0,
                "total_lesson_count": 1,
                "percent": 0,
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_my_courses_progress_success(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    first_section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    second_section = await section_factory(
        course_id=first_section.course_id,
        is_published=True,
        order=1,
    )
    second_course_section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    first_lesson = await create_lesson(db, section_id=first_section.id)
    second_lesson = await create_lesson(db, section_id=second_section.id)
    second_course_lesson = await create_lesson(
        db,
        section_id=second_course_section.id,
    )
    first_step = await create_step(db, lesson_id=first_lesson.id, order=0)
    second_step = await create_step(db, lesson_id=first_lesson.id, order=1)
    third_step = await create_step(db, lesson_id=second_lesson.id, order=0)
    second_course_step = await create_step(
        db,
        lesson_id=second_course_lesson.id,
        order=0,
    )
    await create_enrollment(
        db,
        user_id=user.id,
        course_id=first_section.course_id,
    )
    await create_enrollment(
        db,
        user_id=user.id,
        course_id=second_course_section.course_id,
    )
    for step in [first_step, second_step, second_course_step]:
        await client.post(
            f"/api/progress/steps/{step.id}",
            headers=auth_headers,
        )

    response = await client.get("/api/progress/me/courses", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    progress_by_course = {
        item["course_id"]: item for item in response.json()
    }
    assert progress_by_course == {
        first_section.course_id: {
            "course_id": first_section.course_id,
            "completed_step_count": 2,
            "total_step_count": 3,
            "completed_lesson_count": 1,
            "total_lesson_count": 2,
            "completed_section_count": 1,
            "total_section_count": 2,
            "percent": 67,
        },
        second_course_section.course_id: {
            "course_id": second_course_section.course_id,
            "completed_step_count": 1,
            "total_step_count": 1,
            "completed_lesson_count": 1,
            "total_lesson_count": 1,
            "completed_section_count": 1,
            "total_section_count": 1,
            "percent": 100,
        },
    }
    assert third_step.id is not None


@pytest.mark.asyncio
async def test_get_my_courses_progress_requires_authentication(client):
    response = await client.get("/api/progress/me/courses")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_my_courses_progress_ignores_draft_and_unenrolled_courses(
    client,
    auth_headers,
    course_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    published = await course_factory(slug="published", is_published=True)
    draft = await course_factory(slug="draft", is_published=False)
    await course_factory(slug="not-enrolled", is_published=True)
    await create_enrollment(db, user_id=user.id, course_id=published.id)
    await create_enrollment(db, user_id=user.id, course_id=draft.id)

    response = await client.get("/api/progress/me/courses", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "course_id": published.id,
            "completed_step_count": 0,
            "total_step_count": 0,
            "completed_lesson_count": 0,
            "total_lesson_count": 0,
            "completed_section_count": 0,
            "total_section_count": 0,
            "percent": 0,
        }
    ]


@pytest.mark.asyncio
async def test_get_my_courses_progress_ignores_other_users_progress(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    current_user = await get_user_by_email(db, user_data["email"])
    other_user = await create_user(db)
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_step(db, lesson_id=lesson.id)
    await create_enrollment(
        db,
        user_id=current_user.id,
        course_id=section.course_id,
    )
    await create_enrollment(
        db,
        user_id=other_user.id,
        course_id=section.course_id,
    )
    db.add(StepProgress(user_id=other_user.id, step_id=step.id))
    await db.commit()

    response = await client.get("/api/progress/me/courses", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "course_id": section.course_id,
            "completed_step_count": 0,
            "total_step_count": 1,
            "completed_lesson_count": 0,
            "total_lesson_count": 1,
            "completed_section_count": 0,
            "total_section_count": 1,
            "percent": 0,
        }
    ]


@pytest.mark.asyncio
async def test_get_my_courses_progress_returns_empty_list(
    client,
    auth_headers,
):
    response = await client.get("/api/progress/me/courses", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
