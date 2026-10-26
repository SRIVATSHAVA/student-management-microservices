from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Result Service",
    description="API for managing student academic results",
    version="1.0.0",
)


class ResultCreate(BaseModel):
    student_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    marks: float = Field(ge=0, le=100)


class Result(ResultCreate):
    id: int


results: dict[int, Result] = {}
next_id = 1


@app.get("/health")
def health():
    return {
        "service": "result-service",
        "status": "healthy",
    }


@app.post("/results", response_model=Result, status_code=201)
def create_result(result: ResultCreate):
    global next_id

    record = Result(
        id=next_id,
        **result.model_dump(),
    )

    results[next_id] = record
    next_id += 1

    return record


@app.get("/results", response_model=list[Result])
def list_results():
    return list(results.values())


@app.get("/results/{result_id}", response_model=Result)
def get_result(result_id: int):
    if result_id not in results:
        raise HTTPException(
            status_code=404,
            detail="Result not found",
        )

    return results[result_id]


@app.delete("/results/{result_id}")
def delete_result(result_id: int):
    if result_id not in results:
        raise HTTPException(
            status_code=404,
            detail="Result not found",
        )

    del results[result_id]

    return {"message": "Result deleted successfully"}