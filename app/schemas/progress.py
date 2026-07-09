from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StepProgressPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    step_id: int
    completed_at: datetime


class StepProgressStatus(BaseModel):
    completed: bool


class LessonProgress(BaseModel):
    lesson_id: int
    completed_step_ids: list[int]
    completed_count: int
    total_count: int
    percent: int


class SectionProgress(BaseModel):
    section_id: int
    completed_step_count: int
    total_step_count: int
    completed_lesson_count: int
    total_lesson_count: int
    percent: int


class CourseSectionsProgress(BaseModel):
    course_id: int
    sections: list[SectionProgress]


class CourseProgress(BaseModel):
    course_id: int
    completed_step_count: int
    total_step_count: int
    completed_lesson_count: int
    total_lesson_count: int
    completed_section_count: int
    total_section_count: int
    percent: int
