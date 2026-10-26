from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Course Service",
    description="API for managing course records",
    version="1.0.0",
)


class CourseCreate(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    title: str = Field(min_length=1, max_length=150)
    credits: int = Field(ge=1, le=10)


class Course(CourseCreate):
    id: int


courses: dict[int, Course] = {}
next_id = 1


@app.get("/health")
def health():
    return {
        "service": "course-service",
        "status": "healthy",
    }


@app.post("/courses", response_model=Course, status_code=201)
def create_course(course: CourseCreate):
    global next_id

    record = Course(
        id=next_id,
        **course.model_dump(),
    )

    courses[next_id] = record
    next_id += 1

    return record


@app.get("/courses", response_model=list[Course])
def list_courses():
    return list(courses.values())


@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: int):
    if course_id not in courses:
        raise HTTPException(
            status_code=404,
            detail="Course not found",
        )

    return courses[course_id]


@app.delete("/courses/{course_id}")
def delete_course(course_id: int):
    if course_id not in courses:
        raise HTTPException(
            status_code=404,
            detail="Course not found",
        )

    del courses[course_id]

    return {"message": "Course deleted successfully"}