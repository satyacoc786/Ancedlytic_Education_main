from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Student
from backend.services.scoring import calculate_student_success_score
from backend.services.risk_service import analyze_student_risks

router = APIRouter(prefix="/risks", tags=["At-Risk Students"])

@router.get("")
def get_at_risk_students(
    risk_category: str = Query("all", description="all, academic, placement, both"),
    severity: Optional[str] = Query(None, description="High, Moderate, Low"),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Student)
    if department and department != "All":
        query = query.filter(Student.department == department)

    students = query.all()
    results = []

    for s in students:
        risks = analyze_student_risks(
            s.academic, s.attendance, s.lms, s.placement, s.engagement
        )
        is_acad = risks["academic_risk"]
        is_plc = risks["placement_risk"]

        if not (is_acad or is_plc):
            continue

        if risk_category == "academic" and not is_acad:
            continue
        elif risk_category == "placement" and not is_plc:
            continue
        elif risk_category == "both" and not (is_acad and is_plc):
            continue

        # Severity filter
        if severity:
            max_sev = "High" if (risks["academic_severity"] == "High" or risks["placement_severity"] == "High") else \
                      "Moderate" if (risks["academic_severity"] == "Moderate" or risks["placement_severity"] == "Moderate") else "Low"
            if max_sev.lower() != severity.lower():
                continue

        score_res = calculate_student_success_score(
            s.academic, s.attendance, s.lms, s.placement, s.engagement
        )

        all_indicators = risks["academic_indicators"] + risks["placement_indicators"]

        results.append({
            "id": s.id,
            "name": s.name,
            "department": s.department,
            "semester": s.semester,
            "success_score": score_res["overall_score"],
            "academic_risk": is_acad,
            "academic_severity": risks["academic_severity"],
            "academic_indicators": risks["academic_indicators"],
            "placement_risk": is_plc,
            "placement_severity": risks["placement_severity"],
            "placement_indicators": risks["placement_indicators"],
            "summary_badge": risks["risk_summary_badge"],
            "indicators": all_indicators,
            "last_activity": s.lms.last_activity if s.lms else "Attendance 2 days ago"
        })

    # Sort so High severity and lower scores appear first
    results.sort(key=lambda x: x["success_score"])

    return {
        "total_at_risk": len(results),
        "items": results
    }

