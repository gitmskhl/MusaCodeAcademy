from datetime import datetime

from pydantic import BaseModel, ConfigDict
from app.schemas.course import CoursePublic


class EnrollmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    course_id: int
    created_at: datetime



class EnrollmentWithCourse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    course_id: int
    created_at: datetime
    course: CoursePublic