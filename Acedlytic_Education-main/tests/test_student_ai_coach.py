from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_student_ai_coach_returns_personalized_answer():
    login_res = client.post(
        "/api/auth/login",
        json={"username_or_id": "STU2026001", "password": "student123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/students/STU2026001/coach",
        json={"question": "What should I focus on to improve my academic performance?"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "STU2026001" in body["answer"] or "Rohan" in body["answer"] or "academic" in body["answer"].lower()
    assert body["source"] in {"ollama", "fallback"}
