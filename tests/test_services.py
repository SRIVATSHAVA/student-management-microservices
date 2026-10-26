from fastapi.testclient import TestClient

from services.student_service.app.main import app as student_app
from services.course_service.app.main import app as course_app
from services.result_service.app.main import app as result_app


def test_student_service():
    client = TestClient(student_app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    response = client.post(
        "/students",
        json={
            "name": "Arun Kumar",
            "email": "arun@example.com",
            "department": "Computer Science",
        },
    )
    assert response.status_code == 201
    student_id = response.json()["id"]

    retrieved = client.get(f"/students/{student_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["name"] == "Arun Kumar"


def test_course_service():
    client = TestClient(course_app)

    response = client.post(
        "/courses",
        json={
            "code": "CSE101",
            "title": "Cloud Computing",
            "credits": 4,
        },
    )
    assert response.status_code == 201
    course_id = response.json()["id"]

    retrieved = client.get(f"/courses/{course_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["code"] == "CSE101"


def test_result_service():
    client = TestClient(result_app)

    response = client.post(
        "/results",
        json={
            "student_id": 1,
            "course_id": 1,
            "marks": 85.5,
        },
    )
    assert response.status_code == 201
    result_id = response.json()["id"]

    retrieved = client.get(f"/results/{result_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["marks"] == 85.5


def test_invalid_marks_are_rejected():
    client = TestClient(result_app)

    response = client.post(
        "/results",
        json={
            "student_id": 1,
            "course_id": 1,
            "marks": 150,
        },
    )
    assert response.status_code == 422


def test_missing_student_returns_404():
    client = TestClient(student_app)

    response = client.get("/students/999999")
    assert response.status_code == 404
