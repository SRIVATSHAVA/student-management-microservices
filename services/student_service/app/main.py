from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Student Service",
    description="API for managing student records",
    version="1.0.0",
)


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str
    department: str = Field(min_length=1, max_length=100)


class Student(StudentCreate):
    id: int


students: dict[int, Student] = {}
next_id = 1


@app.get("/health")
def health():
    return {
        "service": "student-service",
        "status": "healthy",
    }


@app.post("/students", response_model=Student, status_code=201)
def create_student(student: StudentCreate):
    global next_id

    record = Student(
        id=next_id,
        **student.model_dump(),
    )

    students[next_id] = record
    next_id += 1

    return record


@app.get("/students", response_model=list[Student])
def list_students():
    return list(students.values())


@app.get("/students/{student_id}", response_model=Student)
def get_student(student_id: int):
    if student_id not in students:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return students[student_id]


@app.delete("/students/{student_id}")
def delete_student(student_id: int):
    if student_id not in students:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    del students[student_id]

    return {"message": "Student deleted successfully"}