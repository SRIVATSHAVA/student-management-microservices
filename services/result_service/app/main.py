
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, String, Integer, Float
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


class Result(Base):
    __tablename__ = "result_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[str] = mapped_column(String(5), nullable=False)


class ResultInput(BaseModel):
    student_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    marks: float = Field(ge=0, le=100)
    grade: str = Field(min_length=1, max_length=5)


class ResultOutput(ResultInput):
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
        raise RuntimeError("Could not initialize result database") from last_error

    yield
    engine.dispose()


app = FastAPI(title="Result Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"service": "result-service", "status": "ok"}


@app.get("/results", response_model=list[ResultOutput])
def list_results(db: Session = Depends(get_db)):
    return db.query(Result).order_by(Result.id).all()


@app.post("/results", response_model=ResultOutput, status_code=201)
def create_result(data: ResultInput, db: Session = Depends(get_db)):
    result = Result(**data.model_dump())
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@app.get("/results/{result_id}", response_model=ResultOutput)
def get_result(result_id: int, db: Session = Depends(get_db)):
    result = db.get(Result, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@app.put("/results/{result_id}", response_model=ResultOutput)
def update_result(
    result_id: int, data: ResultInput, db: Session = Depends(get_db)
):
    result = db.get(Result, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")

    for key, value in data.model_dump().items():
        setattr(result, key, value)

    db.commit()
    db.refresh(result)
    return result


@app.delete("/results/{result_id}")
def delete_result(result_id: int, db: Session = Depends(get_db)):
    result = db.get(Result, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")

    db.delete(result)
    db.commit()
    return {"message": "Result deleted successfully"}
