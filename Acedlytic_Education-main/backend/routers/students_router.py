import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.database import get_db
from backend.models import Student, AuditLog
from backend.services.scoring import calculate_student_success_score
from backend.services.risk_service import analyze_student_risks
from backend.services.ai_coach import generate_student_coach_response
from backend.auth import decode_access_token, get_current_user


class StudentCoachRequest(BaseModel):
    question: str

router = APIRouter(prefix="/students", tags=["Students"])

@router.get("")
def list_students(
    q: Optional[str] = Query(None, description="Search by name, ID or department"),
    department: Optional[str] = Query(None),
    semester: Optional[int] = Query(None),
    risk_type: Optional[str] = Query(None, description="academic, placement, both, at_risk, on_track"),
    sort_by: str = Query("name", description="name, id, cgpa, attendance, score"),
    sort_order: str = Query("asc", description="asc, desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Student)

    if q:
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Student.name.ilike(search),
                Student.id.ilike(search),
                Student.department.ilike(search)
            )
        )

    if department and department != "All":
        query = query.filter(Student.department == department)

    if semester:
        query = query.filter(Student.semester == semester)

    all_students = query.all()
    results = []

    for s in all_students:
        score_res = calculate_student_success_score(
            s.academic, s.attendance, s.lms, s.placement, s.engagement
        )
        risks = analyze_student_risks(
            s.academic, s.attendance, s.lms, s.placement, s.engagement
        )

        is_acad = risks["academic_risk"]
        is_plc = risks["placement_risk"]

        # Filter by risk_type if requested
        if risk_type == "academic" and not is_acad:
            continue
        elif risk_type == "placement" and not is_plc:
            continue
        elif risk_type == "both" and not (is_acad and is_plc):
            continue
        elif risk_type == "at_risk" and not (is_acad or is_plc):
            continue
        elif risk_type == "on_track" and (is_acad or is_plc):
            continue

        flags = []
        if is_acad: flags.append("Academic")
        if is_plc: flags.append("Placement")

        cgpa_val = (s.academic.cgpa if s.academic else 0.0) or 0.0
        att_val = (s.attendance.percentage if s.attendance else 0.0) or 0.0
        last_act = (s.lms.last_activity if s.lms else "Attendance 2 days ago") or "LMS 1 day ago"

        results.append({
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "department": s.department,
            "semester": s.semester,
            "academic_year": s.academic_year,
            "cgpa": cgpa_val,
            "attendance_pct": att_val,
            "success_score": score_res["overall_score"],
            "band": score_res["band"],
            "academic_risk": is_acad,
            "placement_risk": is_plc,
            "risk_flags": flags,
            "last_activity": last_act
        })

    # Sort in Python to support computed scores
    reverse = (sort_order.lower() == "desc")
    if sort_by == "score":
        results.sort(key=lambda x: x["success_score"], reverse=reverse)
    elif sort_by == "cgpa":
        results.sort(key=lambda x: x["cgpa"], reverse=reverse)
    elif sort_by == "attendance":
        results.sort(key=lambda x: x["attendance_pct"], reverse=reverse)
    elif sort_by == "id":
        results.sort(key=lambda x: x["id"], reverse=reverse)
    else:
        results.sort(key=lambda x: x["name"], reverse=reverse)

    total_count = len(results)
    start_idx = (page - 1) * page_size
    paged_results = results[start_idx : start_idx + page_size]

    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 1,
        "items": paged_results
    }

@router.get("/{student_id}")
def get_student_detail(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    score_res = calculate_student_success_score(
        student.academic, student.attendance, student.lms, student.placement, student.engagement
    )
    risk_res = analyze_student_risks(
        student.academic, student.attendance, student.lms, student.placement, student.engagement
    )

    academic_dict = None
    if student.academic:
        try:
            subjects = json.loads(student.academic.subjects_json or "[]")
        except Exception:
            subjects = []
        academic_dict = {
            "cgpa": student.academic.cgpa,
            "semester": student.academic.semester,
            "backlogs": student.academic.backlogs,
            "credits_earned": student.academic.credits_earned,
            "subjects": subjects
        }

    attendance_dict = None
    if student.attendance:
        attendance_dict = {
            "percentage": student.attendance.percentage,
            "present_days": student.attendance.present_days,
            "total_days": student.attendance.total_days,
            "last_date": student.attendance.last_date
        }

    lms_dict = None
    if student.lms:
        lms_dict = {
            "courses_enrolled": student.lms.courses_enrolled,
            "completion_rate": student.lms.completion_rate,
            "assignments_submitted": student.lms.assignments_submitted,
            "assignments_total": student.lms.assignments_total,
            "quiz_avg": student.lms.quiz_avg,
            "forum_posts": student.lms.forum_posts,
            "last_activity": student.lms.last_activity
        }

    placement_dict = None
    if student.placement:
        try:
            skills = json.loads(student.placement.skills_json or "[]")
        except Exception:
            skills = []
        placement_dict = {
            "aptitude_score": student.placement.aptitude_score,
            "coding_score": student.placement.coding_score,
            "comm_score": student.placement.comm_score,
            "resume_score": student.placement.resume_score,
            "mock_interviews": student.placement.mock_interviews,
            "certifications_count": student.placement.certifications_count,
            "readiness_score": student.placement.readiness_score,
            "skills": skills
        }

    engagement_dict = None
    if student.engagement:
        engagement_dict = {
            "score": student.engagement.score,
            "clubs_count": student.engagement.clubs_count,
            "events_attended": student.engagement.events_attended,
            "mentor_meetings": student.engagement.mentor_meetings,
            "last_meeting": student.engagement.last_meeting
        }

    interventions_list = [
        {
            "id": i.id,
            "title": i.title,
            "category": i.category,
            "issue": i.issue,
            "action_plan": i.action_plan,
            "assigned_to": i.assigned_to_name,
            "priority": i.priority,
            "status": i.status,
            "created_at": i.created_at.strftime("%Y-%m-%d") if i.created_at else None,
            "due_date": i.due_date,
            "notes": i.notes
        }
        for i in student.interventions
    ]

    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
        "department": student.department,
        "semester": student.semester,
        "academic_year": student.academic_year,
        "phone": student.phone,
        "avatar": student.name[0].upper() if student.name else "S",
        "status": student.status,
        "academic": academic_dict,
        "attendance": attendance_dict,
        "lms": lms_dict,
        "placement": placement_dict,
        "engagement": engagement_dict,
        "score_analysis": score_res,
        "risk_analysis": risk_res,
        "interventions": interventions_list
    }

@router.get("/{student_id}/portal")
def get_student_portal(
    student_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Student sign-in required")

    payload = decode_access_token(authorization[7:].strip())
    if not payload or payload.get("role") != "student" or payload.get("sub") != student_id:
        raise HTTPException(status_code=403, detail="This student profile is not available to this account")

    return get_student_detail(student_id, db)

@router.post("/{student_id}/coach")
def student_ai_coach(
    student_id: str,
    payload: StudentCoachRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Student sign-in required")

    token = authorization[7:].strip()
    decoded = decode_access_token(token)
    if not decoded or decoded.get("role") != "student" or decoded.get("sub") != student_id:
        raise HTTPException(status_code=403, detail="This student profile is not available to this account")

    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    detail = get_student_detail(student_id, db)
    result = generate_student_coach_response(student, payload.question.strip(), detail["score_analysis"], detail["risk_analysis"])
    return {"answer": result["answer"], "source": result["source"], "student_id": student_id}

@router.put("/{student_id}")
def update_student(
    student_id: str,
    update_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if "name" in update_data: student.name = update_data["name"]
    if "email" in update_data: student.email = update_data["email"]
    if "department" in update_data: student.department = update_data["department"]
    if "phone" in update_data: student.phone = update_data["phone"]
    if "status" in update_data: student.status = update_data["status"]

    # Log audit trail
    log = AuditLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="UPDATE_STUDENT_PROFILE",
        target_type="STUDENT",
        target_id=student_id,
        details=f"Updated details for student {student_id}"
    )
    db.add(log)
    db.commit()
    db.refresh(student)

    return {"message": "Student updated successfully", "id": student.id}

