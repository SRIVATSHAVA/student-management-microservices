
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, String, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session


DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Course(Base):
    __tablename__ = "course_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    credits: Mapped[int] = mapped_column(Integer, nullable=False)


class CourseInput(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str = ""
    credits: int = Field(ge=1, le=30)


class CourseOutput(CourseInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    last_error = None

    for attempt in range(30):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception as exc:
            last_error = exc
            print(f"Database initialization attempt {attempt + 1}/30 failed: {exc}")
            time.sleep(2)
    else:
        raise RuntimeError("Could not initialize course database") from last_error

    yield
    engine.dispose()


app = FastAPI(title="Course Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"service": "course-service", "status": "ok"}


@app.get("/courses", response_model=list[CourseOutput])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).order_by(Course.id).all()


@app.post("/courses", response_model=CourseOutput, status_code=201)
def create_course(data: CourseInput, db: Session = Depends(get_db)):
    course = Course(**data.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.get("/courses/{course_id}", response_model=CourseOutput)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@app.put("/courses/{course_id}", response_model=CourseOutput)
def update_course(
    course_id: int, data: CourseInput, db: Session = Depends(get_db)
):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    for key, value in data.model_dump().items():
        setattr(course, key, value)

    db.commit()
    db.refresh(course)
    return course


@app.delete("/courses/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}
