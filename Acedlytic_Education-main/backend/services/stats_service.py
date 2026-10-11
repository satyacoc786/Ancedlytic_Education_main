from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models import (
    Student, AcademicRecord, AttendanceRecord, LMSEngagement,
    PlacementSkills, EngagementRecord, Intervention
)
from backend.services.scoring import calculate_student_success_score
from backend.services.risk_service import analyze_student_risks

def compute_dashboard_analytics(db: Session) -> Dict[str, Any]:
    students = db.query(Student).all()
    total_students = len(students)
    
    if total_students == 0:
        return {
            "total_students": 0,
            "avg_success_score": 0.0,
            "at_risk_count": 0,
            "at_risk_percent": 0.0,
            "placement_ready_count": 0,
            "placement_ready_percent": 0.0,
            "open_interventions_count": 0,
            "risk_distribution": {"total_at_risk": 0, "academic": 0, "placement": 0, "both": 0},
            "dept_counts": {},
            "segments": {},
            "needing_review": [],
            "recent_interventions": [],
            "insights": []
        }

    scores = []
    academic_risk_count = 0
    placement_risk_count = 0
    both_risks_count = 0
    placement_ready_count = 0
    
    dept_counts: Dict[str, int] = {}
    dept_scores: Dict[str, List[float]] = {}
    
    student_summaries = []

    # Segments
    seg_high_acad_low_plc = 0
    seg_high_acad_high_plc = 0
    seg_low_acad_high_eng = 0
    seg_both_risk = 0
    seg_others = 0

    for s in students:
        dept = s.department or "Others"
        dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        score_res = calculate_student_success_score(
            s.academic, s.attendance, s.lms, s.placement, s.engagement
        )
        sc = score_res["overall_score"]
        scores.append(sc)
        
        if dept not in dept_scores:
            dept_scores[dept] = []
        dept_scores[dept].append(sc)

        risks = analyze_student_risks(
            s.academic, s.attendance, s.lms, s.placement, s.engagement
        )

        is_acad = risks["academic_risk"]
        is_plc = risks["placement_risk"]

        if is_acad and is_plc:
            both_risks_count += 1
        elif is_acad:
            academic_risk_count += 1
        elif is_plc:
            placement_risk_count += 1

        # Placement readiness
        plc_score = (s.placement.readiness_score if s.placement else 0.0) or 0.0
        if plc_score >= 65.0:
            placement_ready_count += 1

        # Segments analysis
        acad_gpa = (s.academic.cgpa if s.academic else 7.0) or 7.0
        eng_score = (s.engagement.score if s.engagement else 70.0) or 70.0

        if is_acad and is_plc:
            seg_both_risk += 1
        elif acad_gpa >= 7.5 and plc_score < 60.0:
            seg_high_acad_low_plc += 1
        elif acad_gpa >= 7.5 and plc_score >= 65.0:
            seg_high_acad_high_plc += 1
        elif acad_gpa < 6.5 and eng_score >= 70.0:
            seg_low_acad_high_eng += 1
        else:
            seg_others += 1

        last_act = (s.lms.last_activity if s.lms else "Attendance 2 days ago") or "LMS 2 days ago"

        student_summaries.append({
            "id": s.id,
            "name": s.name,
            "department": s.department,
            "success_score": sc,
            "academic_risk": is_acad,
            "placement_risk": is_plc,
            "risk_flags": [
                f for f in ["Academic" if is_acad else None, "Placement" if is_plc else None] if f
            ],
            "last_activity": last_act
        })

    # Sort needing review: prioritize students with lowest success scores and highest risks
    needing_review = sorted(
        [s for s in student_summaries if s["academic_risk"] or s["placement_risk"]],
        key=lambda x: x["success_score"]
    )[:10]

    total_at_risk = academic_risk_count + placement_risk_count + both_risks_count
    avg_score = round(sum(scores) / total_students, 1)

    open_interventions = db.query(Intervention).filter(
        Intervention.status.in_(["Open", "In Progress", "Scheduled"])
    ).count()

    recent_interventions_db = db.query(Intervention).order_by(Intervention.created_at.desc()).limit(5).all()
    recent_interventions = [
        {
            "id": i.id,
            "student_id": i.student_id,
            "student_name": i.student.name if i.student else i.student_id,
            "issue": i.issue,
            "assigned_to": i.assigned_to_name,
            "status": i.status,
            "due_date": i.due_date
        }
        for i in recent_interventions_db
    ]

    # Department with highest average
    best_dept = "Computer Science"
    best_avg = 0.0
    for d, d_sc in dept_scores.items():
        if d_sc:
            d_avg = sum(d_sc) / len(d_sc)
            if d_avg > best_avg:
                best_avg = d_avg
                best_dept = d

    insights = [
        {
            "id": 1,
            "text": f"{best_dept} has the highest average success score ({best_avg:.1f}).",
            "time": "2 hours ago",
            "category": "academic"
        },
        {
            "id": 2,
            "text": f"Currently {total_at_risk} at-risk students monitored across campus ({round(total_at_risk / total_students * 100, 1)}% of total).",
            "time": "4 hours ago",
            "category": "risk"
        },
        {
            "id": 3,
            "text": "Placement readiness shows positive momentum with mock interview participation.",
            "time": "6 hours ago",
            "category": "placement"
        },
        {
            "id": 4,
            "text": "LMS assignment completion rate correlates strongly with exam CGPA outcomes.",
            "time": "8 hours ago",
            "category": "lms"
        }
    ]

    return {
        "total_students": total_students,
        "avg_success_score": avg_score,
        "at_risk_count": total_at_risk,
        "at_risk_percent": round((total_at_risk / total_students) * 100, 1),
        "placement_ready_count": placement_ready_count,
        "placement_ready_percent": round((placement_ready_count / total_students) * 100, 1),
        "open_interventions_count": open_interventions,
        "risk_distribution": {
            "total_at_risk": total_at_risk,
            "academic": academic_risk_count,
            "academic_percent": round((academic_risk_count / max(1, total_at_risk)) * 100, 1),
            "placement": placement_risk_count,
            "placement_percent": round((placement_risk_count / max(1, total_at_risk)) * 100, 1),
            "both": both_risks_count,
            "both_percent": round((both_risks_count / max(1, total_at_risk)) * 100, 1)
        },
        "dept_counts": dept_counts,
        "segments": {
            "high_acad_low_plc": seg_high_acad_low_plc,
            "high_acad_high_plc": seg_high_acad_high_plc,
            "low_acad_high_eng": seg_low_acad_high_eng,
            "both_risk": seg_both_risk,
            "others": seg_others
        },
        "needing_review": needing_review,
        "recent_interventions": recent_interventions,
        "insights": insights
    }

