import csv
import io
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.models import (
    Student, AcademicRecord, AttendanceRecord, LMSEngagement,
    PlacementSkills, AuditLog
)

TEMPLATES = {
    "students": "id,name,email,department,semester,academic_year,phone\nCS2026101,Ananya Sen,ananya.s@college.edu,Computer Science,6,2024-2025,+91-9876543210\nEC2026102,Karan Mehta,karan.m@college.edu,Electronics,6,2024-2025,+91-9876543211",
    "academics": "student_id,cgpa,semester,backlogs,credits_earned\nCS2021001,7.85,6,0,128\nEC2021042,5.92,6,1,114",
    "attendance": "student_id,percentage,present_days,total_days\nCS2021001,88.5,177,200\nEC2021042,68.0,136,200",
    "lms": "student_id,completion_rate,assignments_submitted,assignments_total,quiz_avg\nCS2021001,84.0,22,24,78.5\nEC2021042,52.0,14,24,61.0",
    "placement": "student_id,aptitude_score,coding_score,comm_score,resume_score,mock_interviews,readiness_score\nCS2021001,75.0,82.0,78.0,85.0,3,79.5\nEC2021042,55.0,48.0,62.0,58.0,1,54.0"
}

def get_csv_template(import_type: str) -> str:
    return TEMPLATES.get(import_type, TEMPLATES["students"])

def parse_and_validate_csv(csv_content: str, import_type: str, db: Session, commit: bool = False) -> Dict[str, Any]:
    f = io.StringIO(csv_content.strip())
    reader = csv.DictReader(f)
    
    if not reader.fieldnames:
        return {
            "success": False,
            "total_rows": 0,
            "valid_rows": 0,
            "error_rows": 0,
            "errors": ["CSV file is empty or missing headers."],
            "preview_data": []
        }

    expected_cols = {
        "students": ["id", "name", "email", "department"],
        "academics": ["student_id", "cgpa"],
        "attendance": ["student_id", "percentage"],
        "lms": ["student_id", "completion_rate"],
        "placement": ["student_id", "readiness_score"]
    }

    req_cols = expected_cols.get(import_type, ["student_id"])
    missing_cols = [c for c in req_cols if c not in reader.fieldnames]
    if missing_cols:
        return {
            "success": False,
            "total_rows": 0,
            "valid_rows": 0,
            "error_rows": 0,
            "errors": [f"Missing required columns in CSV header: {', '.join(missing_cols)}"],
            "preview_data": []
        }

    total_rows = 0
    valid_rows = 0
    errors: List[str] = []
    preview_data: List[Dict[str, Any]] = []

    seen_ids = set()

    for idx, row in enumerate(reader, start=2): # line 2 is first data row
        total_rows += 1
        row_id = (row.get("id") or row.get("student_id") or "").strip()
        
        if not row_id:
            errors.append(f"Row {idx}: Missing Student ID.")
            continue

        if row_id in seen_ids:
            errors.append(f"Row {idx}: Duplicate Student ID '{row_id}' within file.")
            continue
        seen_ids.add(row_id)

        # Validate existence of student if importing dependent components
        if import_type != "students":
            student_exists = db.query(Student).filter(Student.id == row_id).first()
            if not student_exists:
                errors.append(f"Row {idx}: Student ID '{row_id}' does not exist in student database.")
                continue

        # Data type validations
        row_clean = dict(row)
        try:
            if import_type == "students":
                name = row.get("name", "").strip()
                email = row.get("email", "").strip()
                dept = row.get("department", "").strip()
                if not name or not dept:
                    errors.append(f"Row {idx}: Name and Department are required.")
                    continue
                if commit:
                    stud = db.query(Student).filter(Student.id == row_id).first()
                    if stud:
                        stud.name = name
                        stud.email = email or stud.email
                        stud.department = dept
                        stud.semester = int(row.get("semester", stud.semester))
                    else:
                        stud = Student(
                            id=row_id,
                            name=name,
                            email=email or f"{row_id.lower()}@college.edu",
                            department=dept,
                            semester=int(row.get("semester", 6)),
                            academic_year=row.get("academic_year", "2024-2025"),
                            phone=row.get("phone", "")
                        )
                        db.add(stud)

            elif import_type == "academics":
                cgpa = float(row.get("cgpa", 0.0))
                backlogs = int(row.get("backlogs", 0))
                if not (0.0 <= cgpa <= 10.0):
                    errors.append(f"Row {idx}: CGPA {cgpa} must be between 0.0 and 10.0.")
                    continue
                if commit:
                    rec = db.query(AcademicRecord).filter(AcademicRecord.student_id == row_id).first()
                    if rec:
                        rec.cgpa = cgpa
                        rec.backlogs = backlogs
                    else:
                        db.add(AcademicRecord(student_id=row_id, cgpa=cgpa, backlogs=backlogs))

            elif import_type == "attendance":
                pct = float(row.get("percentage", 0.0))
                if not (0.0 <= pct <= 100.0):
                    errors.append(f"Row {idx}: Attendance percentage {pct} must be between 0 and 100.")
                    continue
                if commit:
                    att = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == row_id).first()
                    if att:
                        att.percentage = pct
                        att.present_days = int(row.get("present_days", int(pct * 2)))
                        att.total_days = int(row.get("total_days", 200))
                    else:
                        db.add(AttendanceRecord(
                            student_id=row_id,
                            percentage=pct,
                            present_days=int(row.get("present_days", int(pct * 2))),
                            total_days=int(row.get("total_days", 200))
                        ))

            elif import_type == "lms":
                comp = float(row.get("completion_rate", 0.0))
                if commit:
                    lms = db.query(LMSEngagement).filter(LMSEngagement.student_id == row_id).first()
                    if lms:
                        lms.completion_rate = comp
                        lms.assignments_submitted = int(row.get("assignments_submitted", lms.assignments_submitted))
                        lms.quiz_avg = float(row.get("quiz_avg", lms.quiz_avg))
                    else:
                        db.add(LMSEngagement(
                            student_id=row_id,
                            completion_rate=comp,
                            assignments_submitted=int(row.get("assignments_submitted", 20)),
                            assignments_total=int(row.get("assignments_total", 24)),
                            quiz_avg=float(row.get("quiz_avg", 75.0))
                        ))

            elif import_type == "placement":
                readiness = float(row.get("readiness_score", 0.0))
                if commit:
                    plc = db.query(PlacementSkills).filter(PlacementSkills.student_id == row_id).first()
                    if plc:
                        plc.readiness_score = readiness
                        plc.aptitude_score = float(row.get("aptitude_score", plc.aptitude_score))
                        plc.coding_score = float(row.get("coding_score", plc.coding_score))
                    else:
                        db.add(PlacementSkills(
                            student_id=row_id,
                            readiness_score=readiness,
                            aptitude_score=float(row.get("aptitude_score", 65.0)),
                            coding_score=float(row.get("coding_score", 60.0)),
                            comm_score=float(row.get("comm_score", 70.0)),
                            resume_score=float(row.get("resume_score", 75.0))
                        ))

            valid_rows += 1
            if len(preview_data) < 10:
                preview_data.append(row_clean)

        except (ValueError, TypeError) as ex:
            errors.append(f"Row {idx}: Data format error ({str(ex)}).")
            continue

    if commit and valid_rows > 0:
        db.commit()

    return {
        "success": len(errors) == 0 or valid_rows > 0,
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "error_rows": len(errors),
        "errors": errors,
        "preview_data": preview_data,
        "committed": commit
    }

