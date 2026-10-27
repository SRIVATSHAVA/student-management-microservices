
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, String, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from fastapi.concurrency import run_in_threadpool


DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "student_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)


class StudentInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=150)
    department: str = Field(min_length=1, max_length=100)


class StudentOutput(StudentInput):
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
        raise RuntimeError("Could not initialize student database") from last_error

    yield
    engine.dispose()


app = FastAPI(title="Student Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"service": "student-service", "status": "ok"}


@app.get("/students", response_model=list[StudentOutput])
def list_students(db: Session = Depends(get_db)):
    return db.query(Student).order_by(Student.id).all()


@app.post("/students", response_model=StudentOutput, status_code=201)
def create_student(data: StudentInput, db: Session = Depends(get_db)):
    if db.query(Student).filter(Student.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")

    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.get("/students/{student_id}", response_model=StudentOutput)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.put("/students/{student_id}", response_model=StudentOutput)
def update_student(
    student_id: int, data: StudentInput, db: Session = Depends(get_db)
):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    duplicate = db.query(Student).filter(
        Student.email == data.email, Student.id != student_id
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Email already exists")

    for key, value in data.model_dump().items():
        setattr(student, key, value)

    db.commit()
    db.refresh(student)
    return student


@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    db.delete(student)
    db.commit()
    return {"message": "Student deleted successfully"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    last_error = None

    for attempt in range(30):
        try:
            # Offload the blocking database creation call onto a worker thread
            await run_in_threadpool(Base.metadata.create_all, bind=engine)
            break
        except Exception as exc:
            last_error = exc
            print(f"Database initialization attempt {attempt + 1}/30 failed: {exc}")
            time.sleep(2)
    else:
        raise RuntimeError("Could not initialize student database") from last_error

    yield
    engine.dispose()
#END

