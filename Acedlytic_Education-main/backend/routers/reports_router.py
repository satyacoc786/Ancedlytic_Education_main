import io
import csv
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Student, Intervention
from backend.services.scoring import calculate_student_success_score
from backend.services.risk_service import analyze_student_risks
from backend.config import settings

router = APIRouter(prefix="/reports", tags=["Reports & Insights"])

@router.get("/methodology")
def get_methodology():
    """Returns official scoring methodology, component weights, missing data policy, and risk rules."""
    return {
        "title": "Acadivance Predictive Scoring & Risk Engine Methodology",
        "formula": "S = 0.35A + 0.20T + 0.15L + 0.20P + 0.10E",
        "components": {
            "A": {
                "name": "Academic Performance",
                "weight": f"{settings.WEIGHT_ACADEMIC * 100:.0f}%",
                "description": "Calculated from normalized CGPA (0–10 scaled to 0–100) minus penalties for active backlogs.",
                "threshold": f"CGPA < {settings.ACADEMIC_RISK_CGPA_THRESHOLD} triggers Academic Risk."
            },
            "T": {
                "name": "Attendance",
                "weight": f"{settings.WEIGHT_ATTENDANCE * 100:.0f}%",
                "description": "Percentage of lecture and lab sessions attended in current semester.",
                "threshold": f"< {settings.ACADEMIC_RISK_ATTENDANCE_THRESHOLD}% triggers Academic Risk (Institutional minimum standard)."
            },
            "L": {
                "name": "LMS Engagement",
                "weight": f"{settings.WEIGHT_LMS * 100:.0f}%",
                "description": "Composite index of course syllabus completion, assignment submission timeliness, and quiz scores.",
                "threshold": f"< {settings.ACADEMIC_RISK_LMS_THRESHOLD}% signals student disengagement."
            },
            "P": {
                "name": "Skills & Placement Preparation",
                "weight": f"{settings.WEIGHT_PLACEMENT * 100:.0f}%",
                "description": "Evaluated based on coding assessments, quantitative aptitude, mock interviews, and resume readiness.",
                "threshold": f"Readiness < {settings.PLACEMENT_RISK_READINESS_THRESHOLD}% triggers Placement Risk."
            },
            "E": {
                "name": "Campus Engagement",
                "weight": f"{settings.WEIGHT_ENGAGEMENT * 100:.0f}%",
                "description": "Participation in co-curricular clubs, technical hackathons, seminars, and mentor check-ins."
            }
        },
        "missing_data_policy": (
            "Missing values are explicitly identified and NOT treated as a zero score. "
            "The system re-normalizes the weights of present components to compute a fair score, "
            "and reports data completeness percentage along with explicit missing data warnings."
        ),
        "risk_classification": {
            "academic_risk": "Rule-based triggers evaluating CGPA, backlogs, attendance, and assignment completion.",
            "placement_risk": "Rule-based triggers evaluating coding aptitude, communication, resume score, and mock interviews.",
            "dual_risk": "Flags students facing concurrent academic and placement difficulties requiring coordinated staff intervention."
        },
        "disclaimer": (
            "Scores and risk indicators are deterministic, transparent rule-based indicators to assist advisors. "
            "They represent institutional guideline flags rather than unchangeable statistical probabilities."
        )
    }

@router.get("/export.csv")
def export_students_csv(
    department: Optional[str] = Query(None),
    risk_filter: Optional[str] = Query("all", description="all, academic, placement, both, at_risk"),
    db: Session = Depends(get_db)
):
    query = db.query(Student)
    if department and department != "All":
        query = query.filter(Student.department == department)

    students = query.all()
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Student ID", "Full Name", "Department", "Semester", "Academic Year",
        "CGPA", "Attendance %", "LMS Completion %", "Placement Readiness %",
        "Success Score", "Performance Band", "Academic Risk", "Placement Risk", "Risk Flags", "Data Completeness %"
    ])

    for s in students:
        sc = calculate_student_success_score(s.academic, s.attendance, s.lms, s.placement, s.engagement)
        rk = analyze_student_risks(s.academic, s.attendance, s.lms, s.placement, s.engagement)

        is_acad = rk["academic_risk"]
        is_plc = rk["placement_risk"]

        if risk_filter == "academic" and not is_acad: continue
        if risk_filter == "placement" and not is_plc: continue
        if risk_filter == "both" and not (is_acad and is_plc): continue
        if risk_filter == "at_risk" and not (is_acad or is_plc): continue

        flags = []
        if is_acad: flags.append("Academic")
        if is_plc: flags.append("Placement")

        cgpa = s.academic.cgpa if s.academic else "N/A"
        att = s.attendance.percentage if s.attendance else "N/A"
        lms_comp = s.lms.completion_rate if s.lms else "N/A"
        plc_read = s.placement.readiness_score if s.placement else "N/A"

        writer.writerow([
            s.id, s.name, s.department, s.semester, s.academic_year,
            cgpa, att, lms_comp, plc_read,
            sc["overall_score"], sc["band"],
            "YES" if is_acad else "NO",
            "YES" if is_plc else "NO",
            ", ".join(flags) if flags else "None",
            f"{sc['data_completeness_percent']}%"
        ])

    csv_data = output.getvalue()
    filename = f"acadivance_report_{department or 'all'}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

