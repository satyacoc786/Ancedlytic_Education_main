import json
from typing import Any, Dict

import httpx

from backend.config import settings


def build_student_context(student: Any, score_analysis: Dict[str, Any], risk_analysis: Dict[str, Any]) -> str:
    parts = [
        f"Student: {student.name} ({student.id})",
        f"Department: {student.department}, Semester: {student.semester}, Academic Year: {student.academic_year}",
        f"Success score: {score_analysis.get('overall_score', 0)} / 100, Band: {score_analysis.get('band', 'Unknown')}",
    ]

    academic = student.academic
    if academic:
        parts.append(
            f"Academic: CGPA {academic.cgpa}, backlogs {academic.backlogs}, credits {academic.credits_earned}."
        )

    attendance = student.attendance
    if attendance:
        parts.append(f"Attendance: {attendance.percentage}% ({attendance.present_days}/{attendance.total_days}).")

    lms = student.lms
    if lms:
        parts.append(
            f"LMS: completion {lms.completion_rate}%, assignments {lms.assignments_submitted}/{lms.assignments_total}, quiz avg {lms.quiz_avg}%."
        )

    placement = student.placement
    if placement:
        parts.append(
            f"Placement: readiness {placement.readiness_score}, aptitude {placement.aptitude_score}, coding {placement.coding_score}, resume {placement.resume_score}."
        )

    engagement = student.engagement
    if engagement:
        parts.append(
            f"Engagement: score {engagement.score}, clubs {engagement.clubs_count}, events {engagement.events_attended}, mentor meetings {engagement.mentor_meetings}."
        )

    if risk_analysis:
        parts.append(
            "Risk status: academic risk "
            f"{risk_analysis.get('academic_risk', False)}, placement risk {risk_analysis.get('placement_risk', False)}."
        )

    if score_analysis.get("positive_factors"):
        parts.append("Strengths: " + "; ".join(score_analysis["positive_factors"][:3]) + ".")
    if score_analysis.get("negative_factors"):
        parts.append("Risk drivers: " + "; ".join(score_analysis["negative_factors"][:3]) + ".")

    return " ".join(parts)


def fallback_student_response(student: Any, question: str, score_analysis: Dict[str, Any], risk_analysis: Dict[str, Any]) -> str:
    q = question.lower()
    score = float(score_analysis.get("overall_score", 0) or 0)
    band = score_analysis.get("band", "Needs Attention")
    academic = student.academic
    attendance = student.attendance
    lms = student.lms
    placement = student.placement

    if score >= 80:
        momentum = "You are already in a strong position and can build on that momentum."
    elif score >= 60:
        momentum = "You are close to a strong outcome; a few focused changes can make a big difference."
    else:
        momentum = "You do not need to start from zero—small, consistent improvements will create visible progress."

    if "attendance" in q and attendance:
        attendance_value = attendance.percentage if attendance else 0
        return (
            f"Your attendance currently stands at {attendance_value}%, which is a solid base for improvement. "
            f"The next step is to protect your academic momentum by attending the next 3 classes without fail and catching up on any missed material the same day. "
            f"Consistency beats intensity here, and this alone can improve both your score and your confidence."
        )

    if "cgpa" in q or "academic" in q or "grade" in q or "course" in q or "study" in q:
        cgpa_value = academic.cgpa if academic else 0
        return (
            f"Student {student.id}, your academic performance is currently at CGPA {cgpa_value}, and that is a strong foundation. "
            f"To improve further, focus on the 2-3 subjects where your understanding is weakest, revise them early each week, and complete all pending assignments before deadlines. "
            f"This approach will lift your results steadily without overwhelming your schedule."
        )

    if "placement" in q or "job" in q or "interview" in q or "resume" in q or "coding" in q:
        readiness = placement.readiness_score if placement else 0
        return (
            f"Your placement readiness is {readiness}, which means you are on a good path. "
            f"The best next move is to sharpen your coding practice, run 2-3 mock interviews each week, and improve the resume sections that still look weak. "
            f"This gives you a stronger profile for recruiters and makes your preparation more targeted."
        )

    if "lms" in q or "online" in q or "assignment" in q or "quiz" in q:
        completion = lms.completion_rate if lms else 0
        return (
            f"Your LMS completion is {completion}%, and that is a good sign of engagement. "
            f"The smartest improvement is to complete pending tasks early, review quiz mistakes, and build a short daily study routine around deadlines. "
            f"This will increase both your learning quality and your course performance."
        )

    strengths = "; ".join(score_analysis.get("positive_factors", ["You are maintaining a stable performance."])[:2])
    risks = "; ".join(score_analysis.get("negative_factors", ["No major risk drivers are visible."])[:2])
    return (
        f"You are currently in the {band} band with a success score of {score:.1f}. "
        f"Your strongest areas are {strengths}. "
        f"The main improvement opportunity is {risks}. "
        f"{momentum} The best next step is to protect your strengths, fix the weakest metric, and stay consistent for the next few weeks."
    )


def generate_ollama_response(prompt: str) -> str | None:
    base_url = (settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
    model = settings.OLLAMA_MODEL or "llama3.2"

    try:
        response = httpx.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "top_p": 0.9},
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
        answer = (data or {}).get("response", "").strip()
        if answer:
            return answer
    except Exception:
        return None
    return None


def generate_student_coach_response(student: Any, question: str, score_analysis: Dict[str, Any], risk_analysis: Dict[str, Any]) -> Dict[str, str]:
    context = build_student_context(student, score_analysis, risk_analysis)
    prompt = (
        "You are a motivating academic advisor for a university student. Use only the student's data below to answer the user's question. "
        "Be encouraging, specific, practical, and concise. Give direct guidance and a realistic next step. Do not be generic.\n\n"
        f"Student data: {context}\n\n"
        f"User question: {question}\n\n"
        "Answer in 3 to 5 sentences, sounding supportive and realistic."
    )

    ai_answer = generate_ollama_response(prompt)
    if ai_answer:
        return {"answer": ai_answer, "source": "ollama"}
    return {"answer": fallback_student_response(student, question, score_analysis, risk_analysis), "source": "fallback"}


def ask_student_ai(student: Any, question: str, score_analysis: Dict[str, Any], risk_analysis: Dict[str, Any]) -> str:
    return generate_student_coach_response(student, question, score_analysis, risk_analysis)["answer"]


def fallback_teacher_response(question: str, analytics: Dict[str, Any]) -> str:
    query = question.lower()
    total = analytics.get("total_students", 0)
    at_risk = analytics.get("at_risk_count", 0)
    risk_distribution = analytics.get("risk_distribution", {})
    departments = analytics.get("dept_counts", {})
    review_list = analytics.get("needing_review", [])
    placement_ready = analytics.get("placement_ready_count", 0)
    placement_percent = analytics.get("placement_ready_percent", 0)

    if any(term in query for term in ("department", "departments", "largest", "most students")):
        top_departments = sorted(departments.items(), key=lambda item: item[1], reverse=True)[:3]
        if top_departments:
            department_summary = ", ".join(f"{name}: {count}" for name, count in top_departments)
            return f"The largest departments by enrollment are {department_summary}. Use these counts to plan support sessions and check whether needs differ by department."
        return "There are no department enrollment records available yet, so I cannot compare departments."

    if any(term in query for term in ("placement", "career", "job", "interview")):
        placement_risk = risk_distribution.get("placement", 0) + risk_distribution.get("both", 0)
        return (
            f"{placement_ready} of {total} students ({placement_percent}%) currently meet the placement-ready threshold. "
            f"{placement_risk} students have a placement risk flag, including students who also have academic support needs. "
            "Start with focused coding, aptitude, resume, or mock-interview support, then review readiness again."
        )

    if any(term in query for term in ("risk", "support", "priority", "who", "students")):
        if review_list:
            priority_students = "; ".join(
                f"{student['name']} ({student['id']}, score {student['success_score']})"
                for student in review_list[:5]
            )
            return (
                f"{at_risk} of {total} students currently have at least one support flag. "
                f"The highest-priority records by success score are: {priority_students}. "
                "Review each student's indicators before assigning a support plan."
            )
        return f"No students are currently flagged for support in the available records ({total} students reviewed)."

    academic_risk = risk_distribution.get("academic", 0) + risk_distribution.get("both", 0)
    placement_risk = risk_distribution.get("placement", 0) + risk_distribution.get("both", 0)
    return (
        f"Across {total} students, the average success score is {analytics.get('avg_success_score', 0)} out of 100. "
        f"{at_risk} students have a support flag: {academic_risk} with academic needs and {placement_risk} with placement needs. "
        f"{placement_ready} students ({placement_percent}%) meet the placement-ready threshold. "
        "A practical next step is to review the highest-priority students and assign a specific follow-up."
    )


def generate_teacher_coach_response(question: str, analytics: Dict[str, Any]) -> Dict[str, str]:
    risk_distribution = analytics.get("risk_distribution", {})
    context = {
        "total_students": analytics.get("total_students", 0),
        "average_success_score": analytics.get("avg_success_score", 0),
        "at_risk_count": analytics.get("at_risk_count", 0),
        "risk_distribution": risk_distribution,
        "placement_ready_count": analytics.get("placement_ready_count", 0),
        "placement_ready_percent": analytics.get("placement_ready_percent", 0),
        "department_counts": analytics.get("dept_counts", {}),
        "highest_priority_students": analytics.get("needing_review", [])[:5],
    }
    prompt = (
        "You are an assistant for college faculty. Answer the teacher's question using only the current cohort data below. "
        "Be clear, concise, and practical. Do not invent statistics, infer causes, or make unsupported claims about students. "
        "When naming a student, use only the provided name and ID. Suggest an appropriate follow-up, not a diagnosis.\n\n"
        f"Current cohort data: {json.dumps(context, ensure_ascii=True)}\n\n"
        f"Teacher question: {question}\n\n"
        "Answer in 3 to 5 sentences and state when the data does not answer the question."
    )

    ai_answer = generate_ollama_response(prompt)
    if ai_answer:
        return {"answer": ai_answer, "source": "ollama"}
    return {"answer": fallback_teacher_response(question, analytics), "source": "fallback"}
