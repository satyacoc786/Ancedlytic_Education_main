import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_login_flow_and_kpis():
    # 1. Login with demo admin
    res = client.post("/api/auth/login", json={"username_or_id": "admin", "password": "admin123"})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["user"]["role"] == "admin"
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Dashboard Summary
    dash_res = client.get("/api/dashboard/summary", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["total_students"] > 100
    assert dash_data["avg_success_score"] > 0
    assert dash_data["at_risk_count"] > 0
    assert len(dash_data["needing_review"]) > 0

    # 3. List Students
    stud_res = client.get("/api/students?page=1&page_size=10", headers=headers)
    assert stud_res.status_code == 200
    stud_data = stud_res.json()
    assert len(stud_data["items"]) == 10

    # 4. Student Detail (CS2021001 Aarav Sharma)
    detail_res = client.get("/api/students/CS2021001", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["name"] == "Aarav Sharma"
    assert "score_analysis" in detail_data
    assert "risk_analysis" in detail_data


def test_teacher_coach_uses_cohort_data_and_requires_staff(monkeypatch):
    from backend.services import ai_coach

    monkeypatch.setattr(ai_coach, "generate_ollama_response", lambda prompt: None)

    teacher_login = client.post(
        "/api/auth/login",
        json={"username_or_id": "TCH1042", "password": "teacher123"},
    )
    assert teacher_login.status_code == 200
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    response = client.post(
        "/api/dashboard/coach",
        json={"question": "Who needs support first?"},
        headers=teacher_headers,
    )
    assert response.status_code == 200
    assert response.json()["source"] == "fallback"
    assert "students currently have at least one support flag" in response.json()["answer"]

    student_login = client.post(
        "/api/auth/login",
        json={"username_or_id": "STU2026001", "password": "student123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    forbidden_response = client.post(
        "/api/dashboard/coach",
        json={"question": "Who needs support first?"},
        headers=student_headers,
    )
    assert forbidden_response.status_code == 403

def test_intervention_crud():
    # Login
    res = client.post("/api/auth/login", json={"username_or_id": "admin", "password": "admin123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create intervention
    payload = {
        "student_id": "CS2021001",
        "title": "Comprehensive Mock Test Mentoring",
        "category": "placement",
        "issue": "Coding Skill Deficit",
        "action_plan": "Bi-weekly coding practice sessions with senior student advisor.",
        "priority": "High",
        "due_date": "May 30, 2025"
    }
    create_res = client.post("/api/interventions", json=payload, headers=headers)
    assert create_res.status_code == 201
    it_data = create_res.json()
    it_id = it_data["id"]
    assert it_data["status"] == "Open"

    # Update status to In Progress
    patch_res = client.patch(
        f"/api/interventions/{it_id}/status",
        json={"status": "In Progress", "notes": "Mentor assigned."},
        headers=headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "In Progress"

def test_csv_validation():
    res = client.post("/api/auth/login", json={"username_or_id": "admin", "password": "admin123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Valid template download
    tpl_res = client.get("/api/integration/template/students", headers=headers)
    assert tpl_res.status_code == 200
    assert "id,name,email,department" in tpl_res.text

def test_student_portal_uses_database_and_student_identity():
    with TestClient(app) as portal_client:
        login_res = portal_client.post(
            "/api/auth/login",
            json={"username_or_id": "STU2026001", "password": "student123"}
        )
        assert login_res.status_code == 200
        assert login_res.json()["user"]["role"] == "student"
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

        portal_res = portal_client.get("/api/students/STU2026001/portal", headers=headers)
        assert portal_res.status_code == 200
        record = portal_res.json()
        assert record["name"] == "Rohan Deshmukh"
        assert record["academic"]["cgpa"] == 8.4
        assert record["attendance"]["percentage"] == 88.0

        other_student_res = portal_client.get("/api/students/CS2021001/portal", headers=headers)
        assert other_student_res.status_code == 403

        invalid_login_res = portal_client.post(
            "/api/auth/login",
            json={"username_or_id": "STU2026001", "password": "wrongpass"}
        )
        assert invalid_login_res.status_code == 401

def test_face_enrollment_requires_password_and_issues_single_use_challenge():
    with TestClient(app) as face_client:
        invalid_res = face_client.post(
            "/api/auth/face/register/options",
            json={"username_or_id": "STU2026001", "password": "wrongpass"}
        )
        assert invalid_res.status_code == 401

        options_res = face_client.post(
            "/api/auth/face/register/options",
            json={"username_or_id": "STU2026001", "password": "student123"}
        )
        assert options_res.status_code == 200
        options = options_res.json()
        assert options["rp"]["id"] == "localhost"
        assert options["authenticatorSelection"]["userVerification"] == "required"

        no_credential_res = face_client.post(
            "/api/auth/face/login/options",
            json={"username_or_id": "STU2026001"}
        )
        assert no_credential_res.status_code == 404

        expired_res = face_client.post(
            "/api/auth/face/register/verify",
            json={"challenge": options["challenge"], "credential": {}}
        )
        assert expired_res.status_code == 400

        replay_res = face_client.post(
            "/api/auth/face/register/verify",
            json={"challenge": options["challenge"], "credential": {}}
        )
        assert replay_res.status_code == 400

def test_new_student_can_register_and_log_in():
    from backend.database import SessionLocal
    from backend.models import Student, User

    student_id = f"NEW{uuid4().hex[:10].upper()}"
    email = f"{uuid4().hex}@example.edu"
    payload = {
        "student_id": student_id,
        "full_name": "New Student",
        "email": email,
        "department": "Computer Science",
        "password": "securepass123",
    }

    try:
        with TestClient(app) as registration_client:
            register_res = registration_client.post("/api/auth/register-student", json=payload)
            assert register_res.status_code == 201
            assert register_res.json()["user"]["role"] == "student"
            assert register_res.json()["user"]["username"] == student_id

            duplicate_res = registration_client.post("/api/auth/register-student", json=payload)
            assert duplicate_res.status_code == 409

            login_res = registration_client.post(
                "/api/auth/login",
                json={"username_or_id": student_id, "password": payload["password"]}
            )
            assert login_res.status_code == 200
            headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
            portal_res = registration_client.get(f"/api/students/{student_id}/portal", headers=headers)
            assert portal_res.status_code == 200
            assert portal_res.json()["name"] == "New Student"
    finally:
        db = SessionLocal()
        db.query(Student).filter(Student.id == student_id).delete(synchronize_session=False)
        db.query(User).filter(User.username == student_id).delete(synchronize_session=False)
        db.commit()
        db.close()

def test_teacher_registration_can_log_in():
    from uuid import uuid4
    from backend.database import SessionLocal
    from backend.models import User

    teacher_id = f"TCH{uuid4().hex[:10].upper()}"
    email = f"teacher{uuid4().hex}@example.edu"
    payload = {
        "teacher_id": teacher_id,
        "full_name": "New Teacher",
        "email": email,
        "password": "teacherpass123",
    }

    try:
        with TestClient(app) as teacher_client:
            register_res = teacher_client.post("/api/auth/register-teacher", json=payload)
            assert register_res.status_code == 201
            assert register_res.json()["user"]["role"] == "faculty"

            duplicate_res = teacher_client.post("/api/auth/register-teacher", json=payload)
            assert duplicate_res.status_code == 409

            login_res = teacher_client.post(
                "/api/auth/login",
                json={"username_or_id": teacher_id, "password": payload["password"]}
            )
            assert login_res.status_code == 200
            assert login_res.json()["user"]["role"] == "faculty"
    finally:
        db = SessionLocal()
        db.query(User).filter(User.username == teacher_id).delete(synchronize_session=False)
        db.commit()
        db.close()

