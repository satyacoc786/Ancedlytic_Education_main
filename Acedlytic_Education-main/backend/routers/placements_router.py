from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Student, PlacementSkills

router = APIRouter(prefix="/placements", tags=["Placement Insights"])

@router.get("/analytics")
def get_placement_analytics(
    department: Optional[str] = Query(None),
    semester: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Student).join(PlacementSkills, Student.id == PlacementSkills.student_id)
    if department and department != "All":
        query = query.filter(Student.department == department)
    if semester:
        query = query.filter(Student.semester == semester)

    students = query.all()
    total = len(students)

    if total == 0:
        return {
            "total_students": 0,
            "ready_count": 0,
            "ready_percent": 0.0,
            "avg_readiness": 0.0,
            "avg_aptitude": 0.0,
            "avg_coding": 0.0,
            "avg_communication": 0.0,
            "avg_resume": 0.0,
            "mock_interviews_completed": 0,
            "distribution": {"high": 0, "medium": 0, "low": 0},
            "dept_readiness": {},
            "skill_gaps": [],
            "students_needing_support": []
        }

    readiness_scores = []
    apt_scores = []
    coding_scores = []
    comm_scores = []
    resume_scores = []
    total_mocks = 0

    dept_map: Dict[str, List[float]] = {}
    high_ready = 0
    med_ready = 0
    low_ready = 0

    needing_support = []

    for s in students:
        p = s.placement
        if not p:
            continue
        r = p.readiness_score or 0.0
        apt = p.aptitude_score or 0.0
        cod = p.coding_score or 0.0
        com = p.comm_score or 0.0
        res = p.resume_score or 0.0
        mocks = p.mock_interviews or 0

        readiness_scores.append(r)
        apt_scores.append(apt)
        coding_scores.append(cod)
        comm_scores.append(com)
        resume_scores.append(res)
        total_mocks += mocks

        # Department map
        d = s.department or "Others"
        if d not in dept_map: dept_map[d] = []
        dept_map[d].append(r)

        if r >= 75.0:
            high_ready += 1
        elif r >= 60.0:
            med_ready += 1
        else:
            low_ready += 1

        # Check if student needs placement support
        if r < 60.0 or cod < 50.0 or apt < 50.0:
            needing_support.append({
                "id": s.id,
                "name": s.name,
                "department": s.department,
                "semester": s.semester,
                "readiness_score": r,
                "coding_score": cod,
                "aptitude_score": apt,
                "comm_score": com,
                "resume_score": res,
                "mock_interviews": mocks,
                "primary_gap": "Coding" if cod < 50 else "Aptitude" if apt < 50 else "Resume / Interviews"
            })

    dept_readiness = {}
    for d, scores in dept_map.items():
        dept_readiness[d] = round(sum(scores) / len(scores), 1) if scores else 0.0

    needing_support.sort(key=lambda x: x["readiness_score"])

    avg_readiness = round(sum(readiness_scores) / total, 1)
    avg_apt = round(sum(apt_scores) / total, 1)
    avg_cod = round(sum(coding_scores) / total, 1)
    avg_comm = round(sum(comm_scores) / total, 1)
    avg_res = round(sum(resume_scores) / total, 1)

    # Skill gaps summary
    skill_gaps = [
        {"skill": "Technical Coding & DSA", "benchmark": 70, "current": avg_cod, "gap": max(0, round(70 - avg_cod, 1))},
        {"skill": "Quantitative Aptitude", "benchmark": 70, "current": avg_apt, "gap": max(0, round(70 - avg_apt, 1))},
        {"skill": "Professional Communication", "benchmark": 75, "current": avg_comm, "gap": max(0, round(75 - avg_comm, 1))},
        {"skill": "Resume & Portfolio Score", "benchmark": 80, "current": avg_res, "gap": max(0, round(80 - avg_res, 1))},
    ]

    return {
        "total_students": total,
        "ready_count": high_ready + med_ready,
        "ready_percent": round(((high_ready + med_ready) / total) * 100, 1),
        "avg_readiness": avg_readiness,
        "avg_aptitude": avg_apt,
        "avg_coding": avg_cod,
        "avg_communication": avg_comm,
        "avg_resume": avg_res,
        "mock_interviews_completed": total_mocks,
        "distribution": {
            "high": high_ready,
            "medium": med_ready,
            "low": low_ready
        },
        "dept_readiness": dept_readiness,
        "skill_gaps": skill_gaps,
        "students_needing_support": needing_support[:15]
    }

